from __future__ import annotations

import pytest
from ada_sensei.evaluation import (
    EVALUATE_RUBRIC,
    RubricDefinition,
    RubricDimension,
    RubricEngine,
    RubricSubcriterion,
    score_requirement,
)
from ada_sensei.models import EvaluationCriterion, Evidence, NotEvaluatedReason
from pydantic import ValidationError


class Fixtures:
    @staticmethod
    def make_requirements():
        return [
            EvaluationCriterion(
                requirement_id="req://r1",
                dimension="functional_requirements",
                weight=0.5,
                score=4,
            ),
            EvaluationCriterion(
                requirement_id="req://r2",
                dimension="functional_requirements",
                weight=0.5,
                score=0,
            ),
        ]


def test_rubric_weights():
    assert EVALUATE_RUBRIC.weights() == {
        "functional_requirements": 0.40,
        "tests": 0.20,
        "code_quality": 0.15,
        "architecture": 0.15,
        "android_practices": 0.10,
    }
    assert abs(sum(EVALUATE_RUBRIC.weights().values()) - 1.0) < 1e-9


def test_rubric_definition_versioning():
    assert EVALUATE_RUBRIC.id == "evaluate-default"
    assert EVALUATE_RUBRIC.version == "v1"
    assert EVALUATE_RUBRIC.ref == "evaluate-default:v1"
    assert EVALUATE_RUBRIC.score_scale_max == 4
    assert EVALUATE_RUBRIC.evidence_policy.renormalize is True
    assert EVALUATE_RUBRIC.evidence_policy.build_dependent == (
        "functional_requirements",
    )
    # A definition is frozen data: no workflow can mutate it in place.
    with pytest.raises(ValidationError):
        EVALUATE_RUBRIC.dimensions[0].weight = 0.9


def test_evaluate_rubric_isolated():
    """RQ-EVA-031: another workflow's rubric cannot change evaluate weights."""
    exam_like = RubricDefinition(
        id="exam-default",
        version="v1",
        dimensions=(
            RubricDimension(id="functional_requirements", weight=0.40),
            RubricDimension(id="exam_process", weight=0.60),
        ),
    )
    assert exam_like.ref == "exam-default:v1"
    assert EVALUATE_RUBRIC.weight_of("tests") == 0.20
    assert EVALUATE_RUBRIC.dimension_ids == [
        "functional_requirements",
        "tests",
        "code_quality",
        "architecture",
        "android_practices",
    ]
    with pytest.raises(KeyError):
        EVALUATE_RUBRIC.dimension("exam_process")


def test_rubric_rejects_weights_that_do_not_sum_to_one():
    with pytest.raises(ValueError, match="top-level weights must sum to 1.0"):
        RubricDefinition(
            id="bad",
            version="v1",
            dimensions=(
                RubricDimension(id="functional_requirements", weight=0.5),
                RubricDimension(id="tests", weight=0.2),
            ),
        )


def test_rubric_rejects_subweights_that_do_not_sum_to_one():
    with pytest.raises(ValueError, match="subcriterion weights must sum to 1.0"):
        RubricDefinition(
            id="bad",
            version="v1",
            dimensions=(
                RubricDimension(
                    id="functional_requirements",
                    weight=1.0,
                    subcriteria=(
                        RubricSubcriterion(id="a", weight=0.5),
                        RubricSubcriterion(id="b", weight=0.2),
                    ),
                ),
            ),
        )


def test_subweights_inside_functional_dimension():
    """RQ-EVA-024: subweights subdivide 40%; they add no top-level weight."""
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {"tests": 4, "code_quality": 3, "architecture": 4, "android_practices": 2},
        Fixtures.make_requirements(),
    )
    assert breakdown.functional_subweight_sum == pytest.approx(1.0)
    # functional = (0.5*4 + 0.5*0) = 2.0
    expected = (
        100
        * (
            0.40 * 2.0 / 4
            + 0.20 * 4 / 4
            + 0.15 * 3 / 4
            + 0.15 * 4 / 4
            + 0.10 * 2 / 4
        )
        / (0.40 + 0.20 + 0.15 + 0.15 + 0.10)
    )
    assert breakdown.overall_score == pytest.approx(expected, abs=0.06)
    assert breakdown.weight_denominator == pytest.approx(1.0)


def test_validate_subweights_rejects_partial_sums():
    with pytest.raises(ValueError, match="subweights must sum to 1.0"):
        EVALUATE_RUBRIC.validate_subweights({"functional_requirements": 0.3})


def test_deterministic_scores():
    engine = RubricEngine(EVALUATE_RUBRIC)
    tests = [
        Evidence(source="test", type="unit_test", status="pass"),
        Evidence(source="test", type="unit_test", status="pass"),
    ]
    assert engine.scorer.score("tests", tests) == (4, None)

    lint_ok = [
        Evidence(
            source="lint",
            type="android_lint",
            status="pass",
            severity="warning",
            message="namespace missing",
        )
    ]
    assert engine.scorer.score("android_practices", lint_ok) == (3, None)


def test_not_evaluated_excluded():
    """RQ-EVA-014: a dimension without evidence leaves the denominator."""
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {
            "tests": None,
            "code_quality": 4,
            "architecture": None,
            "android_practices": None,
        }
    )
    assert breakdown.overall_score == 100.0
    assert breakdown.evaluated_dimensions == ["code_quality"]
    assert set(breakdown.not_evaluated_dimensions) == {
        "functional_requirements",
        "tests",
        "architecture",
        "android_practices",
    }
    assert any("not evaluated" in lim for lim in breakdown.limitations)


def test_partial_functional_renormalizes_over_scored_subset():
    """RQ-EVA-014 / RQ-EVA-024: a requirement without evidence leaves the
    functional denominator instead of failing the whole score.

    The supplied subweights are validated in full (they sum to 1.0), but the
    score is renormalized over the scored subset so an unevaluated requirement is
    excluded rather than counted as a failure.
    """
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {"tests": 4, "code_quality": 3, "architecture": 4, "android_practices": 2},
        [
            EvaluationCriterion(
                requirement_id="req://r1",
                dimension="functional_requirements",
                weight=0.5,
                score=3,
            ),
            EvaluationCriterion(
                requirement_id="req://r2",
                dimension="functional_requirements",
                weight=0.5,
                score=None,
                not_evaluated_reason=NotEvaluatedReason.no_evidence,
            ),
        ],
    )
    # The only scored requirement defines the normalized functional score.
    assert breakdown.dimension_scores["functional_requirements"] == pytest.approx(3.0)
    # The denominator honestly reports the evaluated subset, not the full set.
    assert breakdown.functional_subweight_sum == pytest.approx(0.5)
    assert breakdown.overall_score is not None
    assert "functional_requirements" in breakdown.evaluated_dimensions


def test_malformed_subweights_still_rejected():
    """Validation guards the caller's full subweight set, not the scored subset."""
    engine = RubricEngine(EVALUATE_RUBRIC)
    with pytest.raises(ValueError, match="subweights must sum to 1.0"):
        engine.score(
            {"tests": 4},
            [
                EvaluationCriterion(
                    requirement_id="req://r1",
                    dimension="functional_requirements",
                    weight=0.3,
                    score=3,
                )
            ],
        )


def test_no_dimension_evaluated_no_score():
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {
            "tests": None,
            "code_quality": None,
            "architecture": None,
            "android_practices": None,
        }
    )
    assert breakdown.overall_score is None
    assert breakdown.dimension_scores["tests"] is None
    assert breakdown.limitations


def test_deterministic_reuse():
    """RQ-EVA-032: same definition + same inputs -> same score, no shared state."""
    engine = RubricEngine(EVALUATE_RUBRIC)
    scores = {"tests": 4, "code_quality": 3, "architecture": 4, "android_practices": 1}
    first = engine.score(scores, Fixtures.make_requirements())
    second = engine.score(scores, Fixtures.make_requirements())
    assert first.overall_score == second.overall_score
    assert first.dimension_scores == second.dimension_scores
    # A second engine built on the same definition agrees.
    other = RubricEngine(EVALUATE_RUBRIC)
    assert other.score(scores, Fixtures.make_requirements()).overall_score == (
        first.overall_score
    )


def test_weighted_score():
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {
            "tests": 4,
            "code_quality": 3,
            "architecture": 4,
            "android_practices": 2,
        },
        Fixtures.make_requirements(),
    )
    assert breakdown.overall_score is not None
    expected = (
        100
        * (
            0.40 * 2.0 / 4
            + 0.20 * 4 / 4
            + 0.15 * 3 / 4
            + 0.15 * 4 / 4
            + 0.10 * 2 / 4
        )
        / (0.40 + 0.20 + 0.15 + 0.15 + 0.10)
    )
    assert breakdown.overall_score == pytest.approx(expected, abs=0.06)


def test_score_recomputed_not_taken_from_input():
    """RQ-EVA-007: the engine recomputes; it never trusts a supplied total."""
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {"tests": 4, "code_quality": 4, "architecture": 4, "android_practices": 4},
        [],
    )
    assert breakdown.overall_score == 100.0
    assert breakdown.weighted_sum == pytest.approx(0.60)
    assert breakdown.weight_denominator == pytest.approx(0.60)


def test_build_failure_marks_functional_not_evaluated():
    """RQ-EVA-018: a failed build blocks compilation-dependent criteria."""
    engine = RubricEngine(EVALUATE_RUBRIC)
    breakdown = engine.score(
        {"tests": 4, "code_quality": 4, "architecture": 4, "android_practices": 4},
        Fixtures.make_requirements(),
        build_failed=True,
    )
    assert breakdown.dimension_scores["functional_requirements"] is None
    assert "functional_requirements" in breakdown.not_evaluated_dimensions
    assert any("build_failed" in lim for lim in breakdown.limitations)


def test_requirement_score_passing_unit_test():
    criterion = EvaluationCriterion(
        requirement_id="req://r1",
        evidence=[
            Evidence(source="test", type="unit_test", status="pass"),
            Evidence(source="build", type="compilation", status="pass"),
        ],
    )
    assert score_requirement(criterion) == 4


def test_requirement_score_failing():
    criterion = EvaluationCriterion(
        requirement_id="req://r1",
        evidence=[Evidence(source="test", type="unit_test", status="fail")],
    )
    assert score_requirement(criterion) == 0


def test_requirement_score_no_evidence():
    assert score_requirement(EvaluationCriterion(requirement_id="req://r1")) is None
