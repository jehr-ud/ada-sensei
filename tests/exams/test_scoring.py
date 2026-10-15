"""RQ-EXM-013/015/016/019/020/021/022: deterministic exam scoring."""

from __future__ import annotations

from ada_sensei.exams.architecture import ArchitectureReport
from ada_sensei.exams.models import ArchitectureClaim, ExamRequirement
from ada_sensei.exams.scoring import (
    ExamScorer,
    suggested_grade,
)
from ada_sensei.models import Evidence, NotEvaluatedReason
from exams_helpers import make_attempt, make_definition, make_evidence

FULL_SIGNALS = " ".join(label for label, _ in [
    ("layered packages", 1.0),
    ("viewmodels", 1.0),
    ("repositories", 1.0),
    ("dependency injection", 1.5),
    ("testing structure", 1.0),
    ("domain layer", 1.5),
    ("data layer", 1.0),
    ("navigation", 0.5),
    ("persistence", 0.5),
    ("network boundary", 0.5),
])


def _full_report() -> ArchitectureReport:
    return ArchitectureReport(
        claims=[
            ArchitectureClaim(
                claim=f"the project exposes {FULL_SIGNALS}",
                kind="observed",
                evidence_refs=["ev://structure"],
            )
        ]
    )


def _attempt(no_limits: bool = False) -> object:
    attempt = make_attempt(duration_seconds=0, ask_count=0)
    if no_limits:
        attempt.allowed_duration_seconds = None
        attempt.allowed_ask_count = None
    return attempt


def test_code_quality_from_deterministic_evidence():
    evidence = make_evidence()
    scorer = ExamScorer()
    dimensions = scorer.engine.score_dimensions(evidence.evidence)
    assert dimensions["code_quality"].score == 4
    noisy = make_evidence(
        [
            Evidence(source="detekt", type="static", severity="warning", message="a"),
            Evidence(source="detekt", type="static", severity="error", message="b"),
        ]
    )
    assert scorer.engine.score_dimensions(noisy.evidence)["code_quality"].score == 1


def test_tests_not_evaluated_when_unavailable():
    evidence = make_evidence(
        [
            Evidence(
                id="ev://structure",
                source="structure",
                type="structure",
                status="pass",
                file="app/src/main/java/com/example/app/TaskRepository.kt",
                message="found component Repository",
            )
        ]
    )
    calculation = ExamScorer().score(
        make_definition(), evidence, attempt=_attempt()
    )
    line = next(
        item for item in calculation.lines if item.dimension == "tests"
    )
    assert line.score is None
    assert line.not_evaluated_reason is NotEvaluatedReason.no_evidence


def test_android_practices_from_lint():
    evidence = make_evidence(
        [
            Evidence(id="ev://lint", source="lint", type="static", status="pass"),
            Evidence(source="lint", type="static", severity="warning", message="w1"),
            Evidence(source="lint", type="static", severity="warning", message="w2"),
            Evidence(source="lint", type="static", severity="warning", message="w3"),
        ]
    )
    scorer = ExamScorer()
    dimensions = scorer.engine.score_dimensions(evidence.evidence)
    assert dimensions["android_practices"].score == 3


def test_raw_score_is_deterministic():
    evidence = make_evidence()
    first = ExamScorer().score(
        make_definition(), evidence, attempt=_attempt(), architecture=_full_report()
    )
    second = ExamScorer().score(
        make_definition(), evidence, attempt=_attempt(), architecture=_full_report()
    )
    assert first.raw_score_50 == second.raw_score_50
    assert first.suggested_grade == second.suggested_grade
    assert first.weighted_sum == second.weighted_sum
    assert first.raw_score_50 > 0


def test_raw_score_in_range():
    weak = make_evidence([])
    calculation = ExamScorer().score(
        make_definition(), weak, attempt=_attempt(no_limits=True)
    )
    assert calculation.raw_score_50 is None
    assert calculation.suggested_grade is None

    strong = ExamScorer().score(
        make_definition(),
        make_evidence(),
        attempt=_attempt(),
        architecture=_full_report(),
    )
    assert strong.raw_score_50 == 50
    assert strong.suggested_grade == 5.0
    assert 0 <= strong.raw_score_50 <= 50
    for line in strong.lines:
        assert 0 <= (line.score or 0) <= 4


def test_grade_conversion():
    assert suggested_grade(0) == 1.0
    assert suggested_grade(25) == 3.0
    assert suggested_grade(50) == 5.0
    assert suggested_grade(None) is None
    assert suggested_grade(999) == 5.0
    assert suggested_grade(-5) == 1.0


def test_missing_evidence_never_succeeds():
    definition = make_definition(
        allowed_duration_seconds=None,
        allowed_ask_count=None,
    )
    weak = make_evidence([])
    calculation = ExamScorer().score(definition, weak, attempt=_attempt(no_limits=True))
    criteria = ExamScorer().functional_criteria(definition, weak)
    assert criteria[0].score is None
    assert criteria[0].not_evaluated_reason is NotEvaluatedReason.no_evidence
    assert calculation.raw_score_50 is None
    assert calculation.percentage is None


def test_partially_matched_requirements_still_score():
    """RQ-EXM-012 / RQ-EVA-024: a requirement the project does not evidence is
    ``not_evaluated`` and leaves the functional denominator.

    Only one of two requirements can be matched by the collected evidence. The
    exam must still produce a score: the scored subset renormalizes over 0.5 of
    the functional weight instead of failing the whole attempt.
    """
    definition = make_definition(
        requirements=[
            ExamRequirement(
                requirement_id="req://fr1",
                description="repository",
                weight=0.5,
            ),
            ExamRequirement(
                requirement_id="req://fr2",
                description="offline synchronisation with a remote cache",
                weight=0.5,
            ),
        ]
    )
    # Structure evidence only: the matcher always attaches compilation and
    # unit-test evidence, so omitting them is what leaves a requirement
    # genuinely unevidenced.
    evidence = make_evidence(
        [
            Evidence(
                id="ev://structure",
                source="structure",
                type="structure",
                status="pass",
                file="app/src/main/java/com/example/app/TaskRepository.kt",
                message="found component Repository",
            )
        ]
    )

    criteria = ExamScorer().functional_criteria(definition, evidence)
    assert criteria[0].score is not None, "the matched requirement is scored"
    assert criteria[1].score is None, "the unevidenced requirement is not evaluated"
    assert criteria[1].not_evaluated_reason is NotEvaluatedReason.no_evidence

    calculation = ExamScorer().score(
        definition, evidence, attempt=_attempt(), architecture=_full_report()
    )
    assert calculation.raw_score_50 is not None
    assert 0 <= calculation.raw_score_50 <= 50
    assert calculation.suggested_grade is not None