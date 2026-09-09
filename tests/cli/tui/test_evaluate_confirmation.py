"""Evaluation confirmation in the TUI (RQ-TUI-013 / 014).

Declining confirmation must abort cleanly without starting Gradle; confirming
must proceed through the shared CommandRouter.
"""

from __future__ import annotations

from ada_sensei.cli.commands import EvaluateCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
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
    def make_app(tmp_path) -> AdaSenseiTUI:
        config = Config(project={"path": str(tmp_path / "p")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        router = Router(config=config, client=FakeClient())
        return AdaSenseiTUI(router=router)


def test_confirm_then_run_sets_pending(tmp_path):
    app = Fixtures.make_app(tmp_path)
    app._confirm_then_run(EvaluateCommand())
    assert app._pending_eval is not None


def test_decline_aborts_without_run(tmp_path):
    app = Fixtures.make_app(tmp_path)
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)
    app._confirm_then_run(EvaluateCommand())
    app._resolve_pending_eval(app._pending_eval, "no")
    assert ran == []


def test_confirm_proceeds_to_run(tmp_path):
    app = Fixtures.make_app(tmp_path)
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)
    app._confirm_then_run(EvaluateCommand())
    app._resolve_pending_eval(app._pending_eval, "yes")
    assert len(ran) == 1
    assert isinstance(ran[0], EvaluateCommand)


def test_confirmed_evaluate_skips_prompt(tmp_path):
    app = Fixtures.make_app(tmp_path)
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)
    app._confirm_then_run(EvaluateCommand(yes=True))
    assert app._pending_eval is None
    assert len(ran) == 1
