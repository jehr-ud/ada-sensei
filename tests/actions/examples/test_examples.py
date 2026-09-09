from __future__ import annotations

import pytest
from ada_sensei.actions.base import ActionServices
from ada_sensei.actions.examples import ExamplesAction
from ada_sensei.config import Config
from ada_sensei.context import SessionContext
from ada_sensei.llm.base import LLMClient

GENERATED = {
    "id": "example://gen",
    "concept": "coroutines",
    "level": "intermediate",
    "body": (
        "A coroutine is a suspendable computation. This example explains "
        "why launch works."
    ),
    "common_mistake": None,
    "teaching_questions": [],
    "derived_exercise": None,
    "source": "generated",
}


class FakeClient(LLMClient):
    def __init__(self, payload=None):
        import json

        self.payload = payload if payload is not None else json.dumps(GENERATED)

    def chat(self, messages, *, model=None, temperature=None):
        return ""

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return self.payload


@pytest.fixture
def knowledge_root():
    return ExamplesAction.knowledge_root()


class Services:
    @staticmethod
    def build(tmp_path):
        config = Config(project={"path": str(tmp_path / "proj")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        ctx = SessionContext(config=config, data_dir=tmp_path / "sess")
        ctx.set_student("student://s1")
        return ActionServices.build(config, ctx, FakeClient())


def test_get_or_generate(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run("coroutines")
    assert result.example.source.value in {"curated", "generated"}
    assert result.example.body


def test_identifies_concept(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run("coroutines")
    assert result.example.concept


def test_explains_why(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run("coroutines")
    body = result.example.body.lower()
    assert "why" in body or "because" in body


def test_levels(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run(
        "coroutines", level="advanced"
    )
    assert result.example.level in {"basic", "intermediate", "advanced"}


def test_intentional_mistake(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    curated = ExamplesAction(services, knowledge_root).run("state")
    assert curated.example.common_mistake is not None
    assert curated.example.common_mistake.incorrect_code


def test_mistake_is_flagged(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run("state")
    assert result.example.common_mistake is not None
    assert result.example.common_mistake.explanation


def test_teaching_questions(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run(
        "coroutines", teacher=True
    )
    assert isinstance(result.example.teaching_questions, list)


def test_no_project_touch(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    proj = services.config.project.path
    import os

    assert not os.path.exists(proj)
    ExamplesAction(services, knowledge_root).run("coroutines")
    assert not os.path.exists(proj)


def test_derived_exercise(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run(
        "coroutines", derive_exercise=True
    )
    assert result.example.derived_exercise is not None
    exercise = services.exercises.get(result.example.derived_exercise)
    assert exercise is not None


def test_unknown_topic_error(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    with pytest.raises(Exception) as exc_info:
        ExamplesAction(services, knowledge_root).run("quantum-flux")
    assert "unknown topic" in str(exc_info.value)


def test_teacher_profile(tmp_path, knowledge_root):
    services = Services.build(tmp_path)
    result = ExamplesAction(services, knowledge_root).run(
        "coroutines", teacher=True
    )
    assert result.example.teaching_questions is not None


def test_malformed_fails_cleanly(tmp_path, knowledge_root):
    from ada_sensei.llm import StructuredOutputError

    services = Services.build(tmp_path)
    services.client = FakeClient(payload="{broken")
    with pytest.raises(StructuredOutputError):
        ExamplesAction(services, knowledge_root).run("coroutines")