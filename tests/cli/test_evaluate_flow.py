from __future__ import annotations

from ada_sensei.cli.commands import ErrorResponse, EvaluateCommand
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
    def make_router(tmp_path) -> Router:
        config = Config(project={"path": str(tmp_path / "p")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        return Router(config=config, client=FakeClient())


def test_instrumented_rejected(tmp_path):
    """--instrumented is reserved; it must be reported unsupported (RQ-CLI-015)."""
    router = Fixtures.make_router(tmp_path)
    result = router.dispatch(EvaluateCommand(instrumented=True))
    assert isinstance(result, ErrorResponse)
    assert "instrumented" in result.message.lower()


def test_confirmation_required(tmp_path):
    """Evaluation without --yes must abort before Gradle (RQ-CLI-014/016)."""
    router = Fixtures.make_router(tmp_path)
    result = router.dispatch(EvaluateCommand())
    assert isinstance(result, ErrorResponse)
    assert "confirmation" in result.message.lower() or "abort" in result.message.lower()


def test_yes_reaches_action(tmp_path, monkeypatch):
    captured = {}

    class FakeEvaluate:
        def __init__(self, services):
            self.services = services

        def run(self, inp):
            captured["confirmed"] = inp.confirmed
            captured["instrumented"] = inp.instrumented
            return "ok"

    monkeypatch.setattr(
        "ada_sensei.cli.router.EvaluateAction", lambda services: FakeEvaluate(services)
    )
    router = Fixtures.make_router(tmp_path)
    result = router.dispatch(EvaluateCommand(yes=True))
    assert captured["confirmed"] is True
    assert captured["instrumented"] is False
    assert result == "ok"
