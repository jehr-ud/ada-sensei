"""Evaluation confirmation in the TUI (RQ-TUI-013 / 014).

`evaluate` is a normal selector option; Enter on it runs the normal evaluation
flow and confirmation policy. Declining confirmation must abort cleanly without
starting Gradle; confirming must proceed through the shared CommandRouter.
"""

from __future__ import annotations

from ada_sensei.cli.commands import EvaluateCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient

from conftest import seed_learning_profile, seed_saved_locale


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


def test_selector_evaluate_enter_starts_confirmation_flow(tmp_path):
    # End-to-end: select evaluate from the selector, press Enter, and the TUI
    # requests confirmation before any Gradle execution.
    import asyncio

    app = Fixtures.make_app(tmp_path)
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "Ada")
            seed_learning_profile(tmp_path, "Ada")
            app._resolve_pending_name("Ada")
            await pilot.pause()
            from textual.widgets import Select

            select = app.query_one("#action-select", Select)
            select.value = "evaluate"
            await pilot.pause()
            area = app.query_one("#input")
            area.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert ran == []
            assert app._pending_eval is not None
            app._resolve_pending_eval(app._pending_eval, "no")
            await pilot.pause()
            assert ran == []
            assert app.ui_state.status == "Ready"
            return True

    assert asyncio.run(_run())


def test_selector_evaluate_enter_no_separate_button(tmp_path):
    # evaluate is reached through the same selector used by every other action;
    # there is no Evaluate button anywhere in the UI.
    import asyncio

    app = Fixtures.make_app(tmp_path)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "Ada")
            seed_learning_profile(tmp_path, "Ada")
            app._resolve_pending_name("Ada")
            await pilot.pause()
            assert len(app.query("#evaluate-btn")) == 0
            from textual.widgets import Button

            assert len(app.query(Button)) == 0
            return True

    assert asyncio.run(_run())
