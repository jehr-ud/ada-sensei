"""RQ-EXM-018: the default exam rubric weights and subcriteria."""

from __future__ import annotations

import pytest
from ada_sensei.evaluation.rubric import RubricSubcriterion
from ada_sensei.exams.models import ExamDefinitionError
from ada_sensei.exams.rubric import (
    ASK_USAGE_CRITERION,
    DURATION_CRITERION,
    EXAM_RUBRIC,
    FUNCTIONAL_DIMENSION,
    PROCESS_DIMENSION,
    exam_engine,
    resolve_rubric,
)
from ada_sensei.exams.scoring import ExamScorer


def test_exam_weights():
    weights = EXAM_RUBRIC.weights()
    assert EXAM_RUBRIC.ref == "exam-default:v1"
    assert weights[FUNCTIONAL_DIMENSION] == pytest.approx(0.40)
    assert weights["tests"] == pytest.approx(0.15)
    assert weights["code_quality"] == pytest.approx(0.15)
    assert weights["clean_architecture"] == pytest.approx(0.15)
    assert weights["android_practices"] == pytest.approx(0.05)
    assert weights[PROCESS_DIMENSION] == pytest.approx(0.10)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_process_dimension_has_two_half_subcriteria():
    process = next(d for d in EXAM_RUBRIC.dimensions if d.id == PROCESS_DIMENSION)
    subweights = {s.id: s.weight for s in process.subcriteria}
    assert subweights == {DURATION_CRITERION: 0.5, ASK_USAGE_CRITERION: 0.5}
    assert EXAM_RUBRIC.evidence_policy.build_dependent == (
        FUNCTIONAL_DIMENSION,
        "clean_architecture",
    )
    assert exam_engine().weights() == EXAM_RUBRIC.weights()


def test_unknown_rubric_reference_is_an_error():
    assert resolve_rubric(EXAM_RUBRIC.ref) is EXAM_RUBRIC
    with pytest.raises(ExamDefinitionError):
        resolve_rubric("evaluate-default:v1")


def test_scorer_reads_process_subweights_from_the_rubric():
    """A rubric that reweights ``exam_process`` must actually change the score.

    Guards the dual source of truth that a hardcoded 50/50 in the process
    builders would reintroduce: the declared subweights, not a literal, decide
    the split (RQ-EXM-017/018).
    """
    assert ExamScorer().process_weights() == (0.5, 0.5)

    dimensions = tuple(
        d.model_copy(
            update={
                "subcriteria": (
                    RubricSubcriterion(id=DURATION_CRITERION, weight=0.8),
                    RubricSubcriterion(id=ASK_USAGE_CRITERION, weight=0.2),
                )
            }
        )
        if d.id == PROCESS_DIMENSION
        else d
        for d in EXAM_RUBRIC.dimensions
    )
    custom = EXAM_RUBRIC.model_copy(update={"dimensions": dimensions})
    assert ExamScorer(custom).process_weights() == (0.8, 0.2)


def test_scorer_rejects_a_rubric_missing_the_process_subcriteria():
    """A rubric that drops a declared subcriterion is an error, not a default.

    Falling back to 50/50 would score the exam against weights the rubric never
    declared, which is the silent divergence this wiring exists to prevent.
    """
    dimensions = tuple(
        d.model_copy(update={"subcriteria": ()})
        if d.id == PROCESS_DIMENSION
        else d
        for d in EXAM_RUBRIC.dimensions
    )
    stripped = EXAM_RUBRIC.model_copy(update={"dimensions": dimensions})

    with pytest.raises(ValueError, match="must declare"):
        ExamScorer(stripped).process_weights()