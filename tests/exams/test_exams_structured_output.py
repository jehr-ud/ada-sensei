"""RQ-EXM-025: structured output retries at most three times."""

from __future__ import annotations

import json

import pytest
from ada_sensei.exams.agent import ExamInterpretation, ExamInterpretationAgent
from ada_sensei.exams.models import ProcessMetrics
from ada_sensei.llm.base import LLMClient
from ada_sensei.llm.pipeline import StructuredOutputError, StructuredPipeline
from exams_helpers import make_definition, make_evidence


class AlwaysBadClient(LLMClient):
    def __init__(self):
        self.calls = 0

    def chat(self, messages, *, model=None, temperature=None):
        return "not json"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        self.calls += 1
        return "not json"


class JsonClient(LLMClient):
    def __init__(self, payload: str):
        self.payload = payload
        self.calls = 0

    def chat(self, messages, *, model=None, temperature=None):
        return self.payload

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        self.calls += 1
        return self.payload


def exam_payload(**changes):
    payload = {
        "strengths": [
            {
                "claim": "observed repository",
                "evidence_refs": ["ev://structure"],
                "kind": "strength",
            }
        ],
        "weaknesses": [],
        "recommendations": [],
        "findings": [],
        "feedback": "feedback",
        "next_learning_activity": "practice",
        "limitations": [],
        "architecture": [
            {
                "claim": "repository is separated",
                "evidence_refs": ["ev://structure"],
                "kind": "inferred",
            }
        ],
    }
    payload.update(changes)
    return json.dumps(payload)


def _interpret(client):
    return ExamInterpretationAgent(client).interpret(
        make_definition(),
        make_evidence(),
        ProcessMetrics(ask_count=2, allowed_ask_count=4),
        {"exam_process": 4.0},
    )


def test_three_attempt_limit():
    client = AlwaysBadClient()
    pipeline = StructuredPipeline(client, max_attempts=3)
    with pytest.raises(StructuredOutputError):
        pipeline.run([{"role": "user", "content": "go"}], ExamInterpretation)
    assert client.calls == 3


def test_two_attempt_limit_when_configured():
    client = AlwaysBadClient()
    pipeline = StructuredPipeline(client, max_attempts=2)
    with pytest.raises(StructuredOutputError):
        pipeline.run([{"role": "user", "content": "go"}], ExamInterpretation)
    assert client.calls == 2


def test_agent_without_client_is_available_limitation():
    agent = ExamInterpretationAgent(None)
    metrics = ProcessMetrics(ask_count=2, allowed_ask_count=4)
    interpretation = agent.interpret(
        make_definition(),
        make_evidence(),
        metrics,
        {"exam_process": 4.0},
    )
    assert interpretation.interpretation.limitations
    assert interpretation.strengths() == []
    assert interpretation.weaknesses() == []


def test_valid_exam_interpretation_is_accepted():
    client = JsonClient(exam_payload())

    result = _interpret(client)

    assert client.calls == 1
    assert result.strengths() == ["observed repository"]
    assert result.architecture_claims[0].claim == "repository is separated"


def test_exam_missing_claim_is_rejected():
    client = JsonClient(
        exam_payload(
            strengths=[
                {
                    "evidence_refs": ["ev://structure"],
                    "kind": "strength",
                }
            ]
        )
    )

    with pytest.raises(StructuredOutputError) as excinfo:
        _interpret(client)

    assert "'claim' is a required property" in str(excinfo.value)
    assert client.calls == 3


def test_exam_description_alias_is_rejected():
    client = JsonClient(
        exam_payload(
            strengths=[
                {
                    "description": "observed repository",
                    "evidence_refs": ["ev://structure"],
                    "kind": "strength",
                }
            ]
        )
    )

    with pytest.raises(StructuredOutputError) as excinfo:
        _interpret(client)

    assert "Additional properties are not allowed" in str(excinfo.value)
    assert client.calls == 3


def test_exam_extra_field_is_rejected():
    payload = json.loads(exam_payload())
    payload["instructor_requirements"] = "must not echo the input"
    client = JsonClient(json.dumps(payload))

    with pytest.raises(StructuredOutputError) as excinfo:
        _interpret(client)

    assert "Additional properties are not allowed" in str(excinfo.value)
    assert client.calls == 3


def test_exam_empty_object_is_rejected():
    client = JsonClient("{}")

    with pytest.raises(StructuredOutputError) as excinfo:
        _interpret(client)

    assert "'strengths' is a required property" in str(excinfo.value)
    assert client.calls == 3


def test_exam_prompt_declares_exact_contract():
    prompt = "\n".join(
        item["content"]
        for item in ExamInterpretationAgent(None).messages(
            make_definition(),
            make_evidence(),
            ProcessMetrics(ask_count=2, allowed_ask_count=4),
            {"exam_process": 4.0},
        )
    )

    for field in (
        "strengths",
        "weaknesses",
        "recommendations",
        "findings",
        "feedback",
        "next_learning_activity",
        "limitations",
        "architecture",
        "claim",
        "evidence_refs",
        "kind",
    ):
        assert field in prompt
    assert "description, text, title or summary" in prompt
