"""Reusable evaluation engine, independent of ``EvaluateAction`` (RQ-EVA-028,
RQ-EVA-029, RQ-EVA-032, RQ-EVA-036).
"""

from __future__ import annotations

import pytest
from ada_sensei.evaluation import (
    EVALUATE_RUBRIC,
    EvaluationContext,
    EvaluationEngine,
    EvaluationExecutionPolicy,
    EvidenceContext,
    ProjectContext,
    RequirementMatcher,
    RubricDefinition,
    RubricDimension,
    RubricEngine,
)
from engine_helpers import (
    ScriptedClient,
    StubRunner,
    compilation,
    confirmed_policy,
    detekt,
    full_evidence,
    interpretation_payload,
    lint,
    make_context,
    make_exercise,
    make_project,
    unit_test,
)
from helpers import Fixture


def test_engine_reusable(tmp_path):
    """The engine answers without any caller invoking EvaluateAction."""
    project = Fixture.build_fixture_project(tmp_path)
    engine = EvaluationEngine()
    context = EvaluationContext(student_id="student://s1")

    evidence = engine.collect_evidence(
        make_project(project),
        make_exercise(),
        EvaluationExecutionPolicy(gradle_confirmed=False),
        runner=StubRunner(),
    )
    assert isinstance(evidence, EvidenceContext)
    # Project inspection ran; Gradle did not, because it was not confirmed.
    assert evidence.has_group("structure")
    assert not evidence.has_group("compilation")

    result = engine.evaluate(
        evidence,
        EVALUATE_RUBRIC,
        context,
        exercise=make_exercise(),
        client=None,
    )
    assert result.rubric_id == "evaluate-default"
    assert result.rubric_version == "v1"
    assert result.evidence


def test_evidence_context_is_independent(tmp_path):
    """RQ-EVA-029: the context is workflow-neutral and carries provenance."""
    project = Fixture.build_fixture_project(tmp_path)
    evidence = EvaluationEngine().collect_evidence(
        make_project(project),
        make_exercise(),
        confirmed_policy(),
        runner=StubRunner(),
    )
    assert evidence.project_id is not None
    assert evidence.collected_at_commands == [
        "gradle assembleDebug",
        "gradle testDebugUnitTest",
        "gradle lint",
        "gradle detekt",
    ]
    assert all(e.id and e.id.startswith("ev://") for e in evidence.evidence)
    # Grouping helpers let a second workflow reuse the same collection.
    assert evidence.by_source("lint")
    assert evidence.by_group("compilation")
    assert evidence.by_group("unit_test")


def test_default_scope(tmp_path):
    """RQ-EVA-020: inspection, build, unit tests, lint, detekt."""
    project = Fixture.build_fixture_project(tmp_path)
    evidence = EvaluationEngine().collect_evidence(
        make_project(project),
        None,
        confirmed_policy(),
        runner=StubRunner(),
    )
    assert evidence.has_group("structure")
    assert evidence.has_group("compilation")
    assert evidence.has_group("unit_test")
    assert evidence.by_source("lint")
    assert evidence.by_source("detekt")


def test_instrumented_not_run(tmp_path):
    """RQ-EVA-021: connectedAndroidTest is never part of the collected scope."""
    project = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner()
    EvaluationEngine().collect_evidence(
        make_project(project), None, confirmed_policy(), runner=runner
    )
    assert all("connectedAndroidTest" not in call for call in runner.calls)
    tasks = {call[-1] for call in runner.calls}
    assert tasks == {"assembleDebug", "testDebugUnitTest", "lint", "detekt"}


def test_policy_blocks_gradle_without_confirmation():
    policy = EvaluationExecutionPolicy(gradle_confirmed=False)
    assert policy.gradle_requested() is True
    assert "confirmation required" in (policy.blocked_reason() or "")


def test_policy_rejects_instrumented():
    policy = EvaluationExecutionPolicy(gradle_confirmed=True, run_instrumented=True)
    assert "connectedAndroidTest" in (policy.blocked_reason() or "")


def test_missing_tool_is_a_limitation_not_a_success(tmp_path):
    """RQ-EVA-012: unavailable tooling is reported, never assumed to pass."""
    project = tmp_path / "no-wrapper"
    project.mkdir()
    evidence = EvaluationEngine().collect_evidence(
        make_project(project), None, confirmed_policy(), runner=StubRunner()
    )
    assert evidence.limitations
    assert all(e.status != "pass" for e in evidence.by_group("compilation"))


def test_external_workflow_reuse(tmp_path):
    """RQ-EVA-036: a foreign workflow reuses the engine with its own rubric."""
    project = Fixture.build_fixture_project(tmp_path)
    exam_rubric = RubricDefinition(
        id="exam-default",
        version="v1",
        dimensions=(
            RubricDimension(id="functional_requirements", weight=0.40),
            RubricDimension(id="exam_process", weight=0.60),
        ),
    )
    engine = EvaluationEngine()
    evidence = engine.collect_evidence(
        make_project(project),
        make_exercise(),
        confirmed_policy(),
        runner=StubRunner(),
    )
    result = engine.evaluate(
        evidence,
        exam_rubric,
        EvaluationContext(student_id="student://s2"),
        exercise=make_exercise(),
        client=None,
    )
    assert result.rubric_id == "exam-default"
    assert result.rubric_version == "v1"
    assert "exam_process" in result.dimension_scores
    # The default evaluate rubric is untouched by the foreign workflow.
    assert EVALUATE_RUBRIC.ref == "evaluate-default:v1"
    assert EVALUATE_RUBRIC.weight_of("tests") == 0.20
    assert "exam_process" not in EVALUATE_RUBRIC.dimension_ids


def test_engine_accepts_two_definitions_without_cross_talk():
    a = RubricEngine(EVALUATE_RUBRIC)
    b = RubricEngine(
        RubricDefinition(
            id="exam-default",
            version="v1",
            dimensions=(
                RubricDimension(id="functional_requirements", weight=0.5),
                RubricDimension(id="exam_process", weight=0.5),
            ),
        )
    )
    assert a.weights() != b.weights()
    assert a.ref == "evaluate-default:v1"
    assert b.ref == "exam-default:v1"


def test_evaluate_uses_the_engine_not_a_second_implementation(tmp_path):
    """EvaluateAction orchestrates the shared engine and the default rubric."""
    from ada_sensei.actions.evaluate import EVALUATE_RUBRIC as action_rubric
    from ada_sensei.actions.evaluate import EvaluateAction

    services = Fixture.make_context(
        tmp_path, Fixture.build_fixture_project(tmp_path), client=None
    )
    action = EvaluateAction(services)
    assert isinstance(action.engine, EvaluationEngine)
    assert action.rubric is action_rubric
    assert action.rubric is EVALUATE_RUBRIC


def test_build_failure_marks_requirements_not_evaluated(tmp_path):
    """RQ-EVA-018 plus a blocking limitation."""
    engine = EvaluationEngine()
    evidence = make_context([compilation(status="fail"), unit_test(status="pass")])
    result = engine.evaluate(
        evidence,
        EVALUATE_RUBRIC,
        EvaluationContext(student_id="student://s1"),
        exercise=make_exercise(),
        client=None,
    )
    requirement = next(
        c for c in result.criteria if c.requirement_id == "req://r1"
    )
    assert requirement.score is None
    assert result.dimension_scores["functional_requirements"] is None
    assert any("build_failed" in lim for lim in result.limitations)


def test_no_exercise_is_structural_only():
    engine = EvaluationEngine()
    evidence = make_context(full_evidence())
    result = engine.evaluate(
        evidence, EVALUATE_RUBRIC, EvaluationContext(), client=None
    )
    assert result.exercise_id is None
    assert result.dimension_scores["functional_requirements"] is None
    assert any("no exercise" in lim.lower() for lim in result.limitations)


def test_evidence_is_collected_once_and_reused(tmp_path):
    project = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner()
    engine = EvaluationEngine()
    evidence = engine.collect_evidence(
        make_project(project), make_exercise(), confirmed_policy(), runner=runner
    )
    gradle_calls = len(runner.calls)
    engine.evaluate(
        evidence,
        EVALUATE_RUBRIC,
        EvaluationContext(),
        exercise=make_exercise(),
        client=None,
    )
    # Evaluating a context never re-runs a tool.
    assert len(runner.calls) == gradle_calls


def test_structured_interpretation_is_grounded_in_evidence():
    engine = EvaluationEngine()
    evidence = make_context(full_evidence())
    client = ScriptedClient(
        [
            interpretation_payload(
                strengths=[("clean layering", ["ev://1"])],
                weaknesses=[("no error handling", ["ev://2"])],
            )
        ]
    )
    result = engine.evaluate(
        evidence, EVALUATE_RUBRIC, EvaluationContext(), client=client
    )
    assert result.strengths == ["clean layering"]
    assert result.weaknesses == ["no error handling"]
    assert result.unsupported_claims == []


def test_llm_failure_is_reported_but_scoring_survives():
    engine = EvaluationEngine()
    evidence = make_context(full_evidence())
    client = ScriptedClient(["not json at all"])
    result = engine.evaluate(
        evidence,
        EVALUATE_RUBRIC,
        EvaluationContext(max_attempts=3),
        client=client,
    )
    assert result.overall_score is not None
    assert any("LLM interpretation failed" in lim for lim in result.limitations)


def test_no_client_is_a_limitation_not_a_crash():
    engine = EvaluationEngine()
    result = engine.evaluate(
        make_context(full_evidence()), EVALUATE_RUBRIC, EvaluationContext(), client=None
    )
    assert result.overall_score is not None
    assert result.feedback


def test_matcher_is_callable_without_evaluate_action():
    engine = EvaluationEngine()
    matcher = engine.build_matcher(make_exercise())
    assert isinstance(matcher, RequirementMatcher)
    assert engine.match_requirements(None, make_context([])).criteria == []


def test_project_context_derives_stable_id(tmp_path):
    project = tmp_path / "app"
    project.mkdir()
    first = ProjectContext.from_path(project)
    second = ProjectContext.from_path(str(project))
    assert first.project_id == second.project_id
    assert first.project_id.startswith("project://")


@pytest.mark.parametrize("status", ["pass", "fail"])
def test_build_evidence_status_is_reflected(tmp_path, status):
    project = Fixture.build_fixture_project(tmp_path)
    evidence = EvaluationEngine().collect_evidence(
        make_project(project),
        None,
        confirmed_policy(),
        runner=StubRunner(exit_codes={"assembleDebug": 0 if status == "pass" else 1}),
    )
    build = evidence.by_group("compilation")[0]
    assert build.status == status


def test_lint_and_detekt_evidence_reach_separate_dimensions():
    engine = EvaluationEngine()
    evidence = make_context(
        [compilation(), unit_test(), lint(severity="error", status="fail"),
         detekt(severity="warning")]
    )
    result = engine.evaluate(
        evidence, EVALUATE_RUBRIC, EvaluationContext(), client=None
    )
    # An ERROR lint finding is evidence, not a one-to-one grade deduction: the
    # dimension drops to 1, the rest of the rubric is unaffected.
    assert result.dimension_scores["android_practices"] == 1.0
    assert result.dimension_scores["code_quality"] == 3.0
