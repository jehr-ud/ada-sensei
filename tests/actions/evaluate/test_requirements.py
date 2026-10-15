from __future__ import annotations

from ada_sensei.evaluation import (
    EvidenceContext,
    RequirementMatcher,
    assign_evidence_ids,
)
from ada_sensei.models import Evidence, Exercise, NotEvaluatedReason, Requirement


class Fixtures:
    @staticmethod
    def make_exercise(req_ids, summaries):
        requirements = [
            Requirement(id=rid, summary=summary)
            for rid, summary in zip(req_ids, summaries, strict=True)
        ]
        return Exercise(
            id="exercise://e1",
            title="Task repository",
            requirements=requirements,
            evaluation_criteria=[],
        )

    @staticmethod
    def context(evidence, project_id="project://p1"):
        return EvidenceContext(
            project_id=project_id,
            project_path="/tmp/project",
            evidence=assign_evidence_ids(evidence),
        )


def test_evidence_linked():
    ex = Fixtures.make_exercise(["req://r1"], ["Task repository list"])
    evidence = Fixtures.context(
        [
            Evidence(source="build", type="compilation", status="pass"),
            Evidence(
                source="file",
                type="structure",
                status="pass",
                file="app/src/main/java/TaskRepository.kt",
            ),
        ]
    )
    match = RequirementMatcher(ex).match(evidence)
    assert match.criteria
    criterion = match.criteria[0]
    assert criterion.requirement_id == "req://r1"
    assert criterion.dimension == "functional_requirements"
    assert criterion.score is not None
    # RQ-EVA-005/033: traceable evidence-to-requirement association.
    assert criterion.evidence_refs
    assert set(criterion.evidence_refs) <= evidence.ids()
    assert set(criterion.evidence_refs) <= set(match.matched_evidence_ids)


def test_individual_requirements():
    ex = Fixtures.make_exercise(
        ["req://r1", "req://r2"],
        ["Create and list tasks in the repository", "Persist tasks locally"],
    )
    evidence = Fixtures.context(
        [
            Evidence(source="build", type="compilation", status="pass"),
            Evidence(
                source="test",
                type="unit_test",
                status="pass",
                message="TaskRepositoryTest: 5 tests, 0 failures",
            ),
        ]
    )
    match = RequirementMatcher(ex).match(evidence)
    # RQ-EVA-006: each requirement is evaluated on its own.
    assert [c.requirement_id for c in match.criteria] == ["req://r1", "req://r2"]
    assert all(c.score is not None for c in match.criteria)


def test_match_subweights_normalized():
    ex = Fixtures.make_exercise(["req://r1", "req://r2"], ["one", "two"])
    evidence = Fixtures.context(
        [Evidence(source="build", type="compilation", status="pass")]
    )
    match = RequirementMatcher(ex).match(evidence)
    assert len(match.criteria) == 2
    assert abs(sum(c.weight for c in match.criteria) - 1.0) < 1e-6


def test_declared_criteria_weights_win():
    ex = Fixtures.make_exercise(["req://r1", "req://r2"], ["one", "two"])
    from ada_sensei.models import EvaluationCriterion

    ex.evaluation_criteria = [
        EvaluationCriterion(
            requirement_id="req://r1",
            dimension="functional_requirements",
            weight=0.75,
        ),
        EvaluationCriterion(
            requirement_id="req://r2",
            dimension="functional_requirements",
            weight=0.25,
        ),
    ]
    evidence = Fixtures.context([])
    match = RequirementMatcher(ex).match(evidence)
    assert {c.requirement_id: c.weight for c in match.criteria} == {
        "req://r1": 0.75,
        "req://r2": 0.25,
    }


def test_no_exercise_no_criteria():
    evidence = Fixtures.context(
        [Evidence(source="file", type="structure", status="pass")]
    )
    match = RequirementMatcher(None).match(evidence)
    assert match.criteria == []
    assert match.unmatched_evidence == evidence.evidence


def test_build_failure_marks_not_evaluated():
    """RQ-EVA-018: requirement-level criteria are not evaluated after a failure."""
    ex = Fixtures.make_exercise(["req://r1"], ["list tasks"])
    evidence = Fixtures.context(
        [Evidence(source="build", type="compilation", status="fail")]
    )
    match = RequirementMatcher(ex).match(evidence, build_failed=True)
    assert match.criteria
    criterion = match.criteria[0]
    assert criterion.score is None
    assert criterion.not_evaluated_reason is not None


def test_unmatched_evidence_is_preserved():
    ex = Fixtures.make_exercise(["req://crud"], ["completely unrelated wording"])
    evidence = Fixtures.context(
        [
            Evidence(source="file", type="structure", status="pass", file="a.kt"),
            Evidence(
                source="lint", type="android_lint", status="pass", severity="info"
            ),
        ]
    )
    match = RequirementMatcher(ex).match(evidence)
    assert match.unmatched_evidence
    assert len(match.unmatched_evidence) == len(evidence.evidence)


def test_matcher_reusable():
    """RQ-EVA-033: matching is callable without the /evaluate action."""
    from ada_sensei.evaluation import EvaluationEngine

    ex = Fixtures.make_exercise(["req://r1"], ["task repository"])
    evidence = Fixtures.context(
        [
            Evidence(source="build", type="compilation", status="pass"),
            Evidence(
                source="test",
                type="unit_test",
                status="fail",
                message="TaskRepositoryTest: 2 tests, 1 failures",
            ),
        ]
    )
    engine = EvaluationEngine()
    matcher = engine.build_matcher(ex)
    first = matcher.match(evidence)
    second = engine.match_requirements(ex, evidence)
    assert [c.score for c in first.criteria] == [c.score for c in second.criteria]
    assert first.criteria[0].score == 0


def test_no_evidence_reason_is_recorded():
    ex = Fixtures.make_exercise(["req://r1"], ["list tasks"])
    match = RequirementMatcher(ex).match(Fixtures.context([]))
    assert match.criteria[0].score is None
    assert match.criteria[0].not_evaluated_reason is (
        NotEvaluatedReason.no_evidence
    )
