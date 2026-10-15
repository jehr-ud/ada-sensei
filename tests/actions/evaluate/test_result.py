"""Structured ``EvaluationResult`` contract (RQ-EVA-008, RQ-EVA-014, RQ-EVA-018,
RQ-EVA-022, RQ-EVA-030).
"""

from __future__ import annotations

import json

from ada_sensei.evaluation import (
    EVALUATE_RUBRIC,
    EvaluationContext,
    EvaluationEngine,
    assign_evidence_ids,
)
from ada_sensei.models import EvaluationResult, NotEvaluatedReason
from engine_helpers import (
    ScriptedClient,
    compilation,
    full_evidence,
    interpretation_payload,
    lint,
    make_context,
    make_exercise,
    unit_test,
)


def _evaluate(evidence=None, exercise="default", client=None):
    return EvaluationEngine().evaluate(
        evidence if evidence is not None else make_context(full_evidence()),
        EVALUATE_RUBRIC,
        EvaluationContext(),
        exercise=make_exercise() if exercise != "none" else None,
        client=client,
    )


def test_structured_result():
    """The result is one serializable object with scores, evidence and text."""
    client = ScriptedClient(
        [
            interpretation_payload(
                strengths=[("clear layering", ["ev://1"])],
                weaknesses=[("missing error handling", ["ev://2"])],
                recommendations=[("add repository tests", ["ev://3"])],
            )
        ]
    )
    result = _evaluate(client=client)

    assert isinstance(result, EvaluationResult)
    assert result.id.startswith("result://")
    assert result.rubric_id == EVALUATE_RUBRIC.id
    assert result.rubric_version == EVALUATE_RUBRIC.version
    assert result.overall_score is not None
    assert 0.0 <= result.overall_score <= 100.0
    assert set(result.dimension_scores) == set(EVALUATE_RUBRIC.dimension_ids)
    assert result.strengths == ["clear layering"]
    assert result.weaknesses == ["missing error handling"]
    assert result.recommendations == ["add repository tests"]
    assert result.feedback
    assert result.next_learning_activity
    assert result.evidence
    assert all(e.id for e in result.evidence)
    # Every criterion is either scored or explicitly not evaluated.
    for criterion in result.criteria:
        assert (criterion.score is None) != (criterion.not_evaluated_reason is None)
    # Round-trips through JSON without loss.
    assert EvaluationResult.model_validate(json.loads(result.model_dump_json()))


def test_result_weights_are_carried_by_criteria():
    result = _evaluate()
    functional = [
        c for c in result.criteria if c.dimension == "functional_requirements"
    ]
    assert functional
    assert abs(sum(c.weight for c in functional) - 1.0) < 1e-6
    top_level = {
        c.dimension: c.weight for c in result.criteria if c.requirement_id is None
    }
    assert top_level == {
        "tests": 0.20,
        "code_quality": 0.15,
        "architecture": 0.15,
        "android_practices": 0.10,
    }


def test_result_records_rubric_identity_for_audit():
    """RQ-EVA-030: which rubric produced a stored result is recoverable."""
    result = _evaluate()
    assert result.rubric_ref == f"{EVALUATE_RUBRIC.id}:{EVALUATE_RUBRIC.version}"


def test_not_evaluated_is_explicit_not_zero():
    result = _evaluate(evidence=make_context([compilation(), unit_test()]))
    assert result.dimension_scores["code_quality"] is None
    assert "code_quality" in result.not_evaluated
    assert any("not evaluated" in lim for lim in result.limitations)
    assert result.overall_score is not None


def test_build_failure_criterion_reason_is_reported():
    result = _evaluate(evidence=make_context([compilation(status="fail")]))
    requirement = next(c for c in result.criteria if c.requirement_id == "req://r1")
    assert requirement.score is None
    assert requirement.not_evaluated_reason is not None


def test_criteria_reference_evidence_ids():
    result = _evaluate()
    known = {e.id for e in result.evidence}
    for criterion in result.criteria:
        assert set(criterion.evidence_refs) <= known


def test_evidence_refs_are_stable_and_urn_shaped():
    evidence = assign_evidence_ids(full_evidence())
    ids = [e.id for e in evidence]
    assert len(ids) == len(set(ids)) == len(evidence)
    assert all(i.startswith("ev://") for i in ids)
    # Re-deriving ids from the same list yields the same references.
    assert [e.id for e in assign_evidence_ids(full_evidence())] == ids


def test_unsupported_claims_are_surfaced_in_the_result():
    client = ScriptedClient(
        [
            interpretation_payload(
                strengths=[("good", ["ev://404"])],
                weaknesses=[("bad", [])],
            )
        ]
    )
    result = _evaluate(client=client)
    assert result.strengths == []
    assert result.weaknesses == []
    assert len(result.unsupported_claims) == 2
    kinds = {c.kind for c in result.unsupported_claims}
    assert kinds == {"strengths", "weaknesses"}
    assert all(c.reason for c in result.unsupported_claims)
    assert any("could not be grounded" in lim for lim in result.limitations)


def test_no_exercise_marks_functional_not_evaluated():
    result = _evaluate(exercise="none")
    assert result.exercise_id is None
    assert result.dimension_scores["functional_requirements"] is None
    assert any(
        c.not_evaluated_reason is not None
        for c in result.criteria
        if c.dimension == "functional_requirements"
    )


def test_lint_error_does_not_invent_a_deduction_criterion():
    """RQ-EVA-015: findings inform a dimension score, not 1:1 deductions."""
    result = _evaluate(
        evidence=make_context(
            [compilation(), unit_test(), lint(severity="error", status="fail")]
        )
    )
    assert result.dimension_scores["android_practices"] == 1.0
    # No criterion exists for the individual finding.
    assert not any(
        c.requirement_id and c.requirement_id.startswith("lint")
        for c in result.criteria
    )


def test_not_evaluated_reason_enum_is_declared():
    assert {r.value for r in NotEvaluatedReason} >= {
        "no_evidence",
        "tool_unavailable",
        "build_failed",
        "no_exercise",
    }
