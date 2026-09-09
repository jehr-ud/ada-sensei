from __future__ import annotations

import json

import pytest
from ada_sensei.llm import StructuredOutputError, StructuredPipeline
from ada_sensei.models import Answer


def test_pipeline_no_more_than_three_total_attempts():
    provider = FailingFirstProvider()
    pipeline = StructuredPipeline(provider, max_attempts=3)
    result = pipeline.run([{"role": "user", "content": "ask"}], Answer)
    assert result.response == "ok"
    assert provider.calls == 2


def test_never_silently_accepts_malformed():
    provider = AlwaysBroken()
    with pytest.raises(StructuredOutputError):
        StructuredPipeline(provider, max_attempts=3).run([], Answer)
    assert provider.calls == 3


class FailingFirstProvider:
    def __init__(self):
        self.calls = 0

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ) -> str:
        self.calls += 1
        if self.calls == 1:
            return "not json"
        payload = {
            "id": "answer://x",
            "question": "q",
            "classification": "conceptual",
            "assistance_level": "conceptual_explanation",
            "response": "ok",
            "citations": [],
            "uncertainty": False,
            "created_at": "2026-01-01T00:00:00Z",
        }
        return json.dumps(payload)


class AlwaysBroken:
    def __init__(self):
        self.calls = 0

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ) -> str:
        self.calls += 1
        return "{{{ malformed"
