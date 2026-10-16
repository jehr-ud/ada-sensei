"""Tests for ProgressionPolicyEngine (spec 008-learning-path)."""
from __future__ import annotations

from datetime import UTC, datetime

from ada_sensei.learning.catalog import LearningCatalogLoader
from ada_sensei.learning.models import (
    CriterionResult,
    DimensionResult,
    MasteryAssessment,
)
from ada_sensei.learning.progression import ProgressionPolicyEngine
from ada_sensei.urns import URN


def _now():
    return datetime.now(tz=UTC)


def _make_assessment(
    *,
    student_id: str = "student://test",
    stage_id: str = "kotlin-fundamentals",
    overall_score: float | None = 3.5,
    dim_scores: dict[str, float] | None = None,
    crit_scores: dict[str, float] | None = None,
    evidence_refs: list[str] | None = None,
    exit_challenge: bool = True,
    comprehension: bool = True,
) -> MasteryAssessment:
    loader = LearningCatalogLoader()
    rubrics = loader.load_rubrics("en-US")
    rubric = loader.get_rubric_for_stage(stage_id, rubrics)

    if dim_scores is None:
        dim_scores = {d.id: 3.5 for d in rubric.dimensions}
    if crit_scores is None:
        crit_scores = {c.id: 3.5 for d in rubric.dimensions for c in d.criteria}
    if evidence_refs is None:
        evidence_refs = ["source_code://test/file.kt"]

    dim_results = []
    for dim in rubric.dimensions:
        crit_results = [
            CriterionResult(
                criterion_id=c.id,
                score=crit_scores.get(c.id, 3.5),
                evidence_refs=evidence_refs,
            )
            for c in dim.criteria
        ]
        dim_results.append(
            DimensionResult(
                dimension_id=dim.id,
                score=dim_scores.get(dim.id, 3.5),
                criterion_results=crit_results,
                evidence_refs=evidence_refs,
            )
        )

    return MasteryAssessment(
        id=URN.make("learning"),
        student_id=student_id,
        project_id="project://test",
        stage_id=stage_id,
        rubric_id=rubric.id,
        rubric_version=rubric.version,
        policy_id="mastery-progression-default-v1",
        policy_version="1.0.0",
        catalog_version="1.2.0",
        dimension_results=dim_results,
        overall_score=overall_score,
        evidence_refs=evidence_refs,
        exit_challenge_completed=exit_challenge,
        comprehension_check_completed=comprehension,
        created_at=_now(),
    )


def _engine_and_policy():
    loader = LearningCatalogLoader()
    policy = loader.load_policy("en-US")
    rubrics = loader.load_rubrics("en-US")
    engine = ProgressionPolicyEngine()
    rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
    return engine, policy, rubric


def test_all_gates_pass_returns_ready():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment()
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="android-project-structure")
    assert decision.status == "READY"
    assert decision.to_stage_id == "android-project-structure"
    assert all(g.passed for g in decision.gate_results)


def test_missing_evidence_returns_insufficient():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment(evidence_refs=[])  # no evidence
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="android-project-structure")
    assert decision.status == "INSUFFICIENT_EVIDENCE"
    assert decision.to_stage_id is None


def test_exit_challenge_missing_returns_insufficient():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment(exit_challenge=False)
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="android-project-structure")
    assert decision.status == "INSUFFICIENT_EVIDENCE"


def test_comprehension_missing_returns_insufficient():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment(comprehension=False)
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="android-project-structure")
    assert decision.status == "INSUFFICIENT_EVIDENCE"


def test_critical_criterion_below_threshold_returns_not_ready():
    engine, policy, rubric = _engine_and_policy()
    # Set critical criterion to 1.0 (below 2.0 threshold)
    crit_scores = {}
    for dim in rubric.dimensions:
        for crit in dim.criteria:
            crit_scores[crit.id] = 1.0 if crit.critical else 3.5
    assessment = _make_assessment(crit_scores=crit_scores)
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    assert decision.status == "NOT_READY"
    assert decision.to_stage_id is None


def test_dimension_score_below_threshold_returns_not_ready():
    engine, policy, rubric = _engine_and_policy()
    dim_scores = {d.id: (1.0 if i == 0 else 3.5) for i, d in enumerate(rubric.dimensions)}
    assessment = _make_assessment(dim_scores=dim_scores)
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    assert decision.status == "NOT_READY"


def test_overall_score_below_threshold_returns_not_ready():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment(overall_score=2.0)  # below 3.0
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    assert decision.status == "NOT_READY"


def test_overall_score_at_exact_threshold_passes():
    engine, policy, rubric = _engine_and_policy()
    # Exactly at threshold (3.0) should pass
    assessment = _make_assessment(overall_score=3.0)
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    # Check overall gate specifically
    overall_gate = next(g for g in decision.gate_results if g.gate == "minimum_overall_score")
    assert overall_gate.passed


def test_gate_results_present_for_all_checked_gates():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment()
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    gate_names = {g.gate for g in decision.gate_results}
    assert "require_evidence_for_each_dimension" in gate_names
    assert "minimum_overall_score" in gate_names
    assert "require_exit_challenge" in gate_names
    assert "require_comprehension_check" in gate_names


def test_none_overall_score_returns_not_ready():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment(overall_score=None)
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    assert decision.status in ("NOT_READY", "INSUFFICIENT_EVIDENCE")


def test_progression_decision_records_policy_metadata():
    engine, policy, rubric = _engine_and_policy()
    assessment = _make_assessment()
    decision = engine.evaluate(assessment, rubric, policy, next_stage_id="next")
    assert decision.policy_id == policy.policy_id
    assert decision.policy_version == policy.version
    assert decision.assessment_id == assessment.id
