from __future__ import annotations

import json

import pytest
from ada_sensei.llm import (
    LLMError,
    LLMValidator,
    StructuredOutputError,
    StructuredPipeline,
)
from ada_sensei.models import Exercise, Requirement


class FakeProvider:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ) -> str:
        self.calls += 1
        return self.payloads.pop(0) if self.payloads else '{"malformed":'


def test_schema_validation():
    schema = LLMValidator.schema_for(Exercise)
    exercise = Exercise(
        title="t", statement="s", requirements=[Requirement(summary="r")]
    )
    LLMValidator.validate(exercise.model_dump(mode="json"), schema)


def test_parse_json_strips_fences():
    data = LLMValidator.parse_json('```json\n{"a": 1}\n```')
    assert data == {"a": 1}


def test_parse_json_invalid():
    with pytest.raises(LLMError):
        LLMValidator.parse_json("not json at all")


def test_retry_succeeds_within_budget():
    valid = Exercise(title="t", statement="s").model_dump(mode="json")
    provider = FakeProvider(['{"title":', json.dumps(valid)])
    pipeline = StructuredPipeline(provider, max_attempts=3)
    result = pipeline.run([{"role": "user", "content": "gen"}], Exercise)
    assert result.title == "t"
    assert provider.calls == 2


def test_exhaustion_fails_cleanly():
    provider = FakeProvider(["{broken"] * 10)
    pipeline = StructuredPipeline(provider, max_attempts=3)
    with pytest.raises(StructuredOutputError):
        pipeline.run([{"role": "user", "content": "gen"}], Exercise)
    assert provider.calls == 3


def test_max_attempts_above_three_invalid():
    with pytest.raises(ValueError):
        StructuredPipeline(FakeProvider([]), max_attempts=4)
