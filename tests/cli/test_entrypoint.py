from __future__ import annotations

from ada_sensei.cli.app import CLIApp
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


class AppRouter:
    @staticmethod
    def make(tmp_path) -> Router:
        config = Config(project={"path": str(tmp_path / "p")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        return Router(config=config, client=FakeClient())


def test_unknown_action_user_error(tmp_path, capsys):
    code = CLIApp.run(["frobnicate"], router=AppRouter.make(tmp_path))
    assert code == 1
    assert capsys.readouterr().err != ""


def test_ask_without_question_user_error(tmp_path, capsys):
    code = CLIApp.run(["ask"], router=AppRouter.make(tmp_path))
    assert code == 1


def test_help_exits_zero(tmp_path, capsys):
    code = CLIApp.run(["--help"], router=AppRouter.make(tmp_path))
    assert code == 0
    assert "practice" in capsys.readouterr().out


def test_ask_success_exits_zero(tmp_path, capsys):
    code = CLIApp.run(["ask", "what is MVVM"], router=AppRouter.make(tmp_path))
    assert code == 0


def test_clear_success(tmp_path):
    code = CLIApp.run(["/clear"], router=AppRouter.make(tmp_path))
    assert code == 0