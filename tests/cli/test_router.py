from __future__ import annotations

import pytest
from ada_sensei.cli.commands import (
    AskCommand,
    ErrorResponse,
    ExamplesCommand,
    InternalFailure,
    PracticeCommand,
)
from ada_sensei.cli.errors import CLIError
from ada_sensei.cli.router import Router
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        from ada_sensei.models import Answer

        return Answer(id="answer://a1", response="hello").model_dump_json()


class Fixtures:
    @staticmethod
    def make_config(tmp_path) -> Config:
        config = Config(project={"path": str(tmp_path / "p")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        return config

    @staticmethod
    def make_router(tmp_path, client=None) -> Router:
        return Router(
            config=Fixtures.make_config(tmp_path), client=client or FakeClient()
        )


def test_known_actions_dispatch(tmp_path):
    router = Fixtures.make_router(tmp_path)
    router.context.set_student("tester")
    for cmd in (PracticeCommand(), AskCommand("hi"), ExamplesCommand("mvvm")):
        result = router.dispatch(cmd)
        assert not isinstance(result, (ErrorResponse, InternalFailure))


def test_unknown_action_returns_error_not_raise(tmp_path):
    router = Fixtures.make_router(tmp_path)

    class Bogus:
        pass

    result = router.dispatch(Bogus())
    assert isinstance(result, InternalFailure)


def test_ask_requires_question(tmp_path):
    router = Fixtures.make_router(tmp_path)
    result = router.dispatch(AskCommand("   "))
    assert isinstance(result, ErrorResponse)


def test_examples_requires_topic(tmp_path):
    router = Fixtures.make_router(tmp_path)
    result = router.dispatch(ExamplesCommand("  "))
    assert isinstance(result, ErrorResponse)


def test_unsupported_provider_rejected(tmp_path):
    config = Fixtures.make_config(tmp_path)
    config.llm.provider = "other"
    with pytest.raises(CLIError):
        Router(config=config)


def test_evaluate_exercise_flag(tmp_path, monkeypatch):
    captured = {}

    class FakeEvaluate:
        def __init__(self, services):
            self.services = services

        def run(self, inp):
            captured["exercise"] = inp.exercise_id
            captured["confirmed"] = inp.confirmed
            raise SystemExit(0)

    monkeypatch.setattr(
        "ada_sensei.cli.router.EvaluateAction", lambda services: FakeEvaluate(services)
    )
    router = Fixtures.make_router(tmp_path)
    with pytest.raises(SystemExit):
        router.dispatch(_evaluate_cmd(exercise="exercise://e1"))
    assert captured["exercise"] == "exercise://e1"


def _evaluate_cmd(exercise=None):
    from ada_sensei.cli.commands import EvaluateCommand

    return EvaluateCommand(exercise_id=exercise)
