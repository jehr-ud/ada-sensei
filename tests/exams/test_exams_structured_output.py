"""RQ-EXM-025: structured output retries at most three times."""

from __future__ import annotations

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