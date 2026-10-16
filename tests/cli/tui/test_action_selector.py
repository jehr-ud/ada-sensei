"""Visible action selector and free-text routing (RQ-TUI-004/022/030/033).

The selector persistently offers ask | practice | examples | evaluate. Changing
it updates the input placeholder, the session footer action, and the routing
target for subsequent non-slash free text without clearing the conversation or
the current input. Slash commands bypass free-text routing. `evaluate` lives in
the selector; there is no separate Evaluate button.
"""

from __future__ import annotations

import asyncio

from ada_sensei.cli.commands import (
    AskCommand,
    EvaluateCommand,
    ExamplesCommand,
    PracticeCommand,
)
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import ACTION_OPTIONS, ACTION_PROMPTS, AdaSenseiTUI
from ada_sensei.cli.tui.widgets import SessionFooter
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient
from textual.widgets import Select


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        from ada_sensei.models import Answer

        return Answer(id="answer://a1", response="hello").model_dump_json()


def make_app(tmp_path) -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    return AdaSenseiTUI(router=router)


def mounted(tmp_path, fn):
    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def test_selector_contains_ask_practice_examples_evaluate_and_exam(tmp_path):
    labels = [label for label, _ in ACTION_OPTIONS]
    assert labels == [
        "ask",
        "practice",
        "examples",
        "evaluate",
        "exam-init",
        "exam-finish",
        "learn",
        "diagnose",
        "language",
        "help",
    ]

    async def check(app, pilot):
        select = app.query_one("#action-select", Select)
        values = [str(o[1]) if len(o) > 1 else str(o[0]) for o in select._options]
        expected_values = [value for _, value in ACTION_OPTIONS]
        if values != expected_values:
            # Fallback for Textual versions exposing SelectOption objects.
            try:
                raw = list(select._options)
                alt = [str(getattr(o, "value", o)) for o in raw]
                if alt == expected_values:
                    return True
            except Exception:
                pass
            return False
        return True

    assert mounted(tmp_path, check)


def test_selector_is_persistent_and_visible(tmp_path):
    async def check(app, pilot):
        select = app.query_one("#action-select", Select)
        if hasattr(select, "visible"):
            return select.visible is True
        return True

    assert mounted(tmp_path, check)


def test_no_separate_evaluate_button(tmp_path):
    # RQ-TUI-030/033/034: evaluate is a selector option, not a separate button.
    async def check(app, pilot):
        from textual.widgets import Button

        return len(app.query("#evaluate-btn")) == 0 and len(app.query(Button)) == 0

    assert mounted(tmp_path, check)


def test_selector_change_updates_state(tmp_path):
    async def check(app, pilot):
        select = app.query_one("#action-select", Select)
        select.value = "evaluate"
        await pilot.pause()
        return app.ui_state.action == "evaluate"

    assert mounted(tmp_path, check)


def test_selector_change_updates_placeholder_for_evaluate(tmp_path):
    async def check(app, pilot):
        select = app.query_one("#action-select", Select)
        select.value = "evaluate"
        await pilot.pause()
        placeholder = app.query_one("#input").placeholder
        return placeholder == ACTION_PROMPTS["evaluate"]

    assert mounted(tmp_path, check)


def test_selector_change_updates_footer_action(tmp_path):
    async def check(app, pilot):
        select = app.query_one("#action-select", Select)
        select.value = "evaluate"
        await pilot.pause()
        text = str(app.query_one("#session-footer", SessionFooter).renderable)
        return "Action: evaluate" in text

    assert mounted(tmp_path, check)


def test_selector_change_does_not_clear_conversation(tmp_path):
    async def check(app, pilot):
        app.ui_state.push("existing conversation line")
        select = app.query_one("#action-select", Select)
        select.value = "practice"
        await pilot.pause()
        select.value = "evaluate"
        await pilot.pause()
        return "existing conversation line" in app.ui_state.messages

    assert mounted(tmp_path, check)


def test_selector_change_preserves_input(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        area.text = "typed but not submitted"
        select = app.query_one("#action-select", Select)
        select.value = "examples"
        await pilot.pause()
        select.value = "evaluate"
        await pilot.pause()
        return area.text == "typed but not submitted"

    assert mounted(tmp_path, check)


def test_free_text_routes_to_ask_by_default(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        area = app.query_one("#input")
        area.text = "why does LazyColumn not update?"
        app.action_submit()
        assert isinstance(dispatched[0], AskCommand)
        assert dispatched[0].question == "why does LazyColumn not update?"
        return True

    assert mounted(tmp_path, check)


def test_free_text_routes_to_practice(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        app.ui_state.action = "practice"
        area = app.query_one("#input")
        area.text = "compose-state"
        app.action_submit()
        assert isinstance(dispatched[0], PracticeCommand)
        assert dispatched[0].topic == "compose-state"
        return True

    assert mounted(tmp_path, check)


def test_free_text_routes_to_examples(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        app.ui_state.action = "examples"
        area = app.query_one("#input")
        area.text = "ViewModel"
        app.action_submit()
        assert isinstance(dispatched[0], ExamplesCommand)
        assert dispatched[0].topic == "ViewModel"
        return True

    assert mounted(tmp_path, check)


def test_free_text_routes_to_evaluate_through_confirmation(tmp_path):
    async def direct_check(app, pilot):
        app.ui_state.action = "evaluate"
        cmd = app._command_from_line("anything I type")
        assert isinstance(cmd, EvaluateCommand)
        assert cmd.confirmed is False
        return True

    assert mounted(tmp_path, direct_check)


def test_empty_free_text_practice_topic_is_none(tmp_path):
    async def direct_check(app, pilot):
        app.ui_state.action = "practice"
        cmd = app._command_from_line("")
        assert isinstance(cmd, PracticeCommand)
        assert cmd.topic is None
        return True

    assert mounted(tmp_path, direct_check)


def test_slash_commands_bypass_selector(tmp_path):
    async def direct_check(app, pilot):
        for action in ("ask", "practice", "examples", "evaluate"):
            app.ui_state.action = action
            cmd = app._command_from_line("/ask what is a composable?")
            assert isinstance(cmd, AskCommand)
            assert cmd.question == "what is a composable?"
        return True

    assert mounted(tmp_path, direct_check)


def test_slash_evaluate_is_parsed_not_free_text(tmp_path):
    async def direct_check(app, pilot):
        # /evaluate is parsed as a slash command, never ask free-text content.
        cmd = app._command_from_line("/evaluate --yes")
        assert isinstance(cmd, EvaluateCommand)
        assert cmd.confirmed is True

        # Free text routed to ask/practice/examples never becomes an
        # EvaluateCommand; only the evaluate selector option routes to it.
        for action in ("ask", "practice", "examples"):
            app.ui_state.action = action
            free = app._command_from_line("run the checks please")
            assert not isinstance(free, EvaluateCommand)
        return True

    assert mounted(tmp_path, direct_check)