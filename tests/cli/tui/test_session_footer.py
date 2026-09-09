"""Persistent session footer (RQ-TUI-032).

The bottom footer permanently shows Student, Score, AI model, current action,
and operation status. Values come from authoritative sources only: student
identity from SessionContext, score from the most recent evaluation result, and
the AI model from the configured LLM implementation. The TUI never calculates a
score or hardcodes a model.
"""

from __future__ import annotations

import asyncio

from ada_sensei.actions.evaluate import EvalResult
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import SessionFooter
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


def make_app(tmp_path, model="qwen2.5-coder:7b") -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    config.llm.model = model
    router = Router(config=config, client=FakeClient())
    return AdaSenseiTUI(router=router)


def mounted(tmp_path, fn, name="Ada"):
    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            if name:
                app._resolve_pending_name(name)
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def footer_text(app) -> str:
    return str(app.query_one("#session-footer", SessionFooter).renderable)


def test_footer_shows_student(tmp_path):
    async def check(app, pilot):
        return "Student: Ada" in footer_text(app)

    assert mounted(tmp_path, check, name="Ada")


def test_footer_shows_neutral_when_student_missing(tmp_path):
    async def check(app, pilot):
        return "Student: —" in footer_text(app)

    assert mounted(tmp_path, check, name="")


def test_score_neutral_when_no_evaluation(tmp_path):
    async def check(app, pilot):
        return "Score: —" in footer_text(app)

    assert mounted(tmp_path, check)


def test_score_appears_after_evaluation(tmp_path):
    async def check(app, pilot):
        # Simulate the authoritative router capturing the score after an
        # evaluation result is dispatched.
        app.router._last_score = 85.0
        app.refresh_footer()
        return "Score: 85.0" in footer_text(app)

    assert mounted(tmp_path, check)


def test_model_from_configuration(tmp_path):
    async def check(app, pilot):
        return "AI: qwen2.5-coder:7b" in footer_text(app)

    assert mounted(tmp_path, check)


def test_model_not_hardcoded_in_tui(tmp_path):
    source = ""
    for path in ("ada_sensei/cli/tui/app.py", "ada_sensei/cli/tui/widgets.py"):
        with open(path, encoding="utf-8") as fh:
            source += fh.read()
    assert "Qwen3-Coder-30B" not in source
    assert "qwen2.5-coder:7b" not in source


def test_footer_shows_action(tmp_path):
    async def check(app, pilot):
        return "Action: ask" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_updates_when_action_changes(tmp_path):
    async def check(app, pilot):
        app.ui_state.action = "practice"
        app.refresh_footer()
        return "Action: practice" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_updates_on_score_change(tmp_path):
    async def check(app, pilot):
        assert "Score: —" in footer_text(app)
        app.router._last_score = 72.5
        app.refresh_footer()
        return "Score: 72.5" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_updates_when_identity_changes(tmp_path):
    async def check(app, pilot):
        app._handle_name_command("/name Bob")
        app.refresh_footer()
        return "Student: Bob" in footer_text(app)

    assert mounted(tmp_path, check, name="Ada")


def test_footer_shows_ready_status(tmp_path):
    async def check(app, pilot):
        return "Ready" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_shows_running_status(tmp_path):
    async def check(app, pilot):
        app._set_busy(True, "Running")
        return "Running" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_shows_evaluating_status(tmp_path):
    async def check(app, pilot):
        app._set_busy(True, "Evaluating")
        return "Evaluating" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_shows_waiting_confirmation_status(tmp_path):
    async def check(app, pilot):
        app._status("Waiting for confirmation")
        return "Waiting for confirmation" in footer_text(app)

    assert mounted(tmp_path, check)


def test_footer_shows_error_status(tmp_path):
    async def check(app, pilot):
        app._set_busy(False, "Error")
        return "Error" in footer_text(app)

    assert mounted(tmp_path, check)


def test_router_dispatches_evaluate_and_records_score(tmp_path):
    # The authoritative score source: the router records overall_score when an
    # EvaluateCommand is dispatched to the EvaluateAction.
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())

    from ada_sensei.models import EvaluationResult

    captured = {}

    class StubEval:
        def __init__(self, services):
            pass

        def run(self, inp):
            captured["confirmed"] = inp.confirmed
            return EvalResult(result=EvaluationResult(overall_score=66.0))

    import ada_sensei.cli.router as router_module

    original = router_module.EvaluateAction
    router_module.EvaluateAction = StubEval
    try:
        from ada_sensei.cli.commands import EvaluateCommand

        result = router.dispatch(EvaluateCommand(yes=True))
    finally:
        router_module.EvaluateAction = original

    assert isinstance(result, EvalResult)
    assert router.last_score() == 66.0