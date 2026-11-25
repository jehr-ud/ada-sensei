"""Structured LLM output contract: 3-attempt limit and grounding validation
(RQ-EVA-034, RQ-EVA-035).
"""

from __future__ import annotations

import json

import pytest
from ada_sensei.evaluation import (
    EVALUATE_RUBRIC,
    EvaluationAgent,
    EvaluationContext,
    EvaluationCriterionInput,
    EvaluationEngine,
    LLMRequirementEvaluator,
    assign_evidence_ids,
)
from ada_sensei.evaluation.agent import (
    EvaluationInterpretation,
    GroundedClaim,
    GroundedInterpretation,
)
from ada_sensei.evaluation.llm_evaluators import CriterionDecisionBatch
from ada_sensei.llm.base import LLMClient
from ada_sensei.llm.pipeline import StructuredOutputError
from ada_sensei.llm.validation import LLMValidator
from ada_sensei.models import Evidence
from engine_helpers import (
    ScriptedClient,
    full_evidence,
    interpretation_payload,
    make_context,
)


class CountingClient(LLMClient):
    """Always returns the same payload and counts provider calls."""

    def __init__(self, payload: str):
        self.payload = payload
        self.calls = 0

    def chat(self, messages, *, model=None, temperature=None):
        self.calls += 1
        return self.payload

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        self.calls += 1
        return self.payload


def _context():
    return make_context(full_evidence())


def test_three_attempt_limit():
    """RQ-EVA-034: 1 initial attempt + at most 2 retries, then explicit failure."""
    client = CountingClient("this is not JSON at all")
    agent = EvaluationAgent(client, max_attempts=3)
    with pytest.raises(StructuredOutputError) as excinfo:
        agent.interpret(_context(), {"tests": 4.0})
    assert "3 total attempt" in str(excinfo.value)
    assert client.calls == 3
    assert client.calls <= 3


def test_two_attempts_when_configured():
    # Valid JSON but the wrong schema, so every attempt fails validation.
    client = CountingClient(json.dumps({"strengths": "not a list"}))
    agent = EvaluationAgent(client, max_attempts=2)
    with pytest.raises(StructuredOutputError):
        agent.interpret(_context(), {})
    assert client.calls == 2


def test_valid_output_accepted_on_first_attempt():
    client = CountingClient(interpretation_payload(strengths=[("ok", ["ev://1"])]))
    agent = EvaluationAgent(client, max_attempts=3)
    result = agent.interpret(_context(), {"tests": 4.0})
    assert client.calls == 1
    assert result.strengths() == ["ok"]


def test_retry_recovers_from_malformed_output():
    client = ScriptedClient(
        [
            "not json",
            interpretation_payload(strengths=[("recovered", ["ev://1"])]),
        ]
    )
    agent = EvaluationAgent(client, max_attempts=3)
    result = agent.interpret(_context(), {"tests": 4.0})
    assert result.strengths() == ["recovered"]


def test_unsupported_claim_rejected():
    """RQ-EVA-035: a claim citing nothing resolvable is reported, not accepted."""
    context = _context()
    interpretation = EvaluationInterpretation(
        strengths=[
            GroundedClaim(
                claim="grounded", evidence_refs=["ev://1"], kind="strength"
            )
        ],
        weaknesses=[
            GroundedClaim(
                claim="invented", evidence_refs=[], kind="weakness"
            )
        ],
        recommendations=[
            GroundedClaim(
                claim="dangling ref", evidence_refs=["ev://999"], kind="recommendation"
            )
        ],
        findings=[
            GroundedClaim(
                claim="half right",
                evidence_refs=["ev://2", "ev://998"],
                kind="finding",
            )
        ],
        feedback="feedback",
        next_learning_activity="practice",
        limitations=[],
    )
    grounded = EvaluationAgent.ground(interpretation, context)

    assert grounded.strengths() == ["grounded"]
    assert grounded.weaknesses() == []
    assert grounded.recommendations() == []
    assert grounded.findings() == []
    assert len(grounded.unsupported_claims) == 3
    reasons = {c.claim: c.reason for c in grounded.unsupported_claims}
    assert "cites no evidence" in reasons["invented"]
    assert "ev://999" in reasons["dangling ref"]
    assert "ev://998" in reasons["half right"]


def test_all_claims_supported_is_accepted_whole():
    context = _context()
    grounded = EvaluationAgent.ground(
        EvaluationInterpretation(
            strengths=[
                GroundedClaim(claim="a", evidence_refs=["ev://1"], kind="strength")
            ],
            weaknesses=[
                GroundedClaim(claim="b", evidence_refs=["ev://2"], kind="weakness")
            ],
            recommendations=[],
            findings=[],
            feedback="feedback",
            next_learning_activity="practice",
            limitations=[],
        ),
        context,
    )
    assert grounded.unsupported_claims == []
    assert len(grounded.accepted_claims()) == 2


def test_grounding_is_context_specific():
    """A ref valid for one project must not validate against another."""
    other = make_context(
        assign_evidence_ids([Evidence(source="file", type="structure", status="pass")])
    )
    grounded = EvaluationAgent.ground(
        EvaluationInterpretation(
            strengths=[
                GroundedClaim(claim="a", evidence_refs=["ev://3"], kind="strength")
            ],
            weaknesses=[],
            recommendations=[],
            findings=[],
            feedback="feedback",
            next_learning_activity="practice",
            limitations=[],
        ),
        other,
    )
    assert grounded.strengths() == []
    assert len(grounded.unsupported_claims) == 1


def test_pipeline_failure_still_yields_a_result():
    """Deterministic scoring survives; the failure becomes a limitation."""
    engine = EvaluationEngine()
    result = engine.evaluate(
        make_context(full_evidence()),
        EVALUATE_RUBRIC,
        EvaluationContext(max_attempts=1),
        client=CountingClient("<xml>not json</xml>"),
    )
    assert result.overall_score is not None
    assert any("LLM interpretation failed" in lim for lim in result.limitations)
    assert result.strengths == []
    assert result.weaknesses == []


def test_schema_rejects_wrong_types_then_accepts_valid():
    """Malformed claim objects are rejected by schema validation, not coerced."""
    bad = json.dumps(
        {
            "strengths": "not a list",
            "weaknesses": [],
            "recommendations": [],
            "findings": [],
            "feedback": "f",
            "next_learning_activity": "n",
            "limitations": [],
        }
    )
    agent = EvaluationAgent(CountingClient(bad), max_attempts=3)
    try:
        agent.interpret(_context(), {})
    except Exception:  # noqa: BLE001
        pass
    else:  # pragma: no cover
        raise AssertionError("invalid schema was accepted")


def test_grounded_interpretation_exposes_plain_text():
    grounded = GroundedInterpretation(
        interpretation=EvaluationInterpretation(
            strengths=[
                GroundedClaim(claim="s", evidence_refs=["ev://1"], kind="strength")
            ],
            weaknesses=[
                GroundedClaim(claim="w", evidence_refs=["ev://2"], kind="weakness")
            ],
            recommendations=[
                GroundedClaim(
                    claim="r", evidence_refs=["ev://3"], kind="recommendation"
                )
            ],
            findings=[
                GroundedClaim(claim="f", evidence_refs=["ev://4"], kind="finding")
            ],
            feedback="feedback",
            next_learning_activity="practice",
            limitations=[],
        )
    )
    assert grounded.strengths() == ["s"]
    assert grounded.weaknesses() == ["w"]
    assert grounded.recommendations() == ["r"]
    assert grounded.findings() == ["f"]


def missing_claim_payload():
    return json.dumps(
        {
            "strengths": [
                {
                    "evidence_refs": ["ev://1"],
                    "kind": "strength",
                }
            ],
            "weaknesses": [],
            "recommendations": [],
            "findings": [],
            "feedback": "feedback",
            "next_learning_activity": "practice",
            "limitations": [],
        }
    )


def test_valid_claim_response_is_accepted():
    client = CountingClient(interpretation_payload(strengths=[("valid", ["ev://1"])]))
    result = EvaluationAgent(client, max_attempts=3).interpret(
        _context(), {"tests": 4.0}
    )

    assert client.calls == 1
    assert result.strengths() == ["valid"]


def test_missing_claim_response_is_rejected():
    client = CountingClient(missing_claim_payload())

    with pytest.raises(StructuredOutputError) as excinfo:
        EvaluationAgent(client, max_attempts=3).interpret(_context(), {})

    assert "'claim' is a required property" in str(excinfo.value)
    assert client.calls == 3


def test_missing_claim_never_marks_criteria_pass():
    client = CountingClient(missing_claim_payload())
    result = EvaluationEngine().evaluate(
        make_context([]),
        EVALUATE_RUBRIC,
        EvaluationContext(max_attempts=3),
        client=client,
    )

    assert client.calls == 3
    assert result.overall_score is None
    assert all(item.score is None for item in result.criteria)
    assert all(item.not_evaluated_reason is not None for item in result.criteria)
    assert any("'claim' is a required property" in lim for lim in result.limitations)


def test_prompts_declare_all_required_fields():
    client = ScriptedClient([json.dumps({"criteria": []})])
    LLMRequirementEvaluator(client).evaluate(
        [EvaluationCriterionInput(criterion_id="AC1", description="criterion")],
        _context(),
    )
    criterion_prompt = "\n".join(item["content"] for item in client.calls[0])
    interpretation_prompt = "\n".join(
        item["content"] for item in EvaluationAgent(None).messages(_context(), {})
    )

    for field in (
        "criterion_id",
        "status",
        "reason",
        "evidence_ids",
        "limitations",
        "recommended_action",
        "confidence",
        "criteria",
        "clean_architecture",
        "mvvm",
    ):
        assert field in criterion_prompt
    for field in (
        "claim",
        "evidence_refs",
        "kind",
        "strengths",
        "weaknesses",
        "recommendations",
        "findings",
        "feedback",
        "next_learning_activity",
        "limitations",
    ):
        assert field in interpretation_prompt


def test_criterion_schema_requires_all_contract_fields():
    schema = LLMValidator.schema_for(CriterionDecisionBatch)
    definition = schema["$defs"]["LLMCriterionDecision"]

    assert set(definition["required"]) == {
        "criterion_id",
        "status",
        "reason",
        "evidence_ids",
        "limitations",
        "recommended_action",
        "confidence",
    }
    assert definition["additionalProperties"] is False
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"criteria"}


def test_interpretation_schema_requires_claim_and_forbids_extra_fields():
    schema = LLMValidator.schema_for(EvaluationInterpretation)
    claim = schema["$defs"]["GroundedClaim"]

    assert set(claim["required"]) == {"claim", "evidence_refs", "kind"}
    assert claim["additionalProperties"] is False
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "strengths",
        "weaknesses",
        "recommendations",
        "findings",
        "feedback",
        "next_learning_activity",
        "limitations",
    }
