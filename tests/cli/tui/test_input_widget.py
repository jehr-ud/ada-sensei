"""Editable multi-line TextArea input and focus (RQ-TUI-030/031).

The TUI must provide an always-visible, editable multi-line TextArea that
accepts ordinary keyboard input, executes the selected action with Enter,
inserts newlines with Shift+Enter, and restores focus after
completion/error/cancellation. No global binding may consume ordinary
printable input.
"""

from __future__ import annotations

import asyncio

from ada_sensei.cli.commands import AskCommand, ExamplesCommand, PracticeCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import PromptArea
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


def make_app(tmp_path) -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    return AdaSenseiTUI(router=router)


def mounted(tmp_path, fn, name="Ada"):
    """Run async ``fn(app, pilot)`` inside a mounted ``run_test``."""

    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name(name)
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def test_input_is_a_textarea(tmp_path):
    from textual.widgets import TextArea

    async def check(app, pilot):
        return isinstance(app.query_one("#input"), TextArea)

    assert mounted(tmp_path, check)


def test_input_is_prompt_area(tmp_path):
    async def check(app, pilot):
        return isinstance(app.query_one("#input"), PromptArea)

    assert mounted(tmp_path, check)


def test_layout_usable_at_80x24(tmp_path):
    async def check(app, pilot):
        input_box = app.query_one("#input")
        selector = app.query_one("#action-select")
        footer = app.query_one("#session-footer")
        return (
            input_box.region.height >= 5
            and selector.region.height >= 1
            and footer.region.height >= 1
            and input_box.region
            and not input_box.region.intersection(footer.region)
        )

    assert mounted(tmp_path, check)


def test_input_editable_when_ready(tmp_path):
    async def check(app, pilot):
        return app.query_one("#input").disabled is False

    assert mounted(tmp_path, check)


def test_input_receives_focus(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        area.focus()
        await pilot.pause()
        return app.focused is area

    assert mounted(tmp_path, check)


def test_text_can_be_inserted(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        area.text = "hello world"
        return area.text == "hello world"

    assert mounted(tmp_path, check)


def test_enter_executes_selected_action(tmp_path):
    async def _run():
        app = make_app(tmp_path)
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            area = app.query_one("#input")
            area.focus()
            await pilot.pause()
            for ch in "hi":
                await pilot.press(ch)
            await pilot.press("enter")
            await pilot.pause()
            assert area.text == ""
            assert len(dispatched) == 1
            assert isinstance(dispatched[0], AskCommand)
            assert dispatched[0].question == "hi"
            return True

    assert asyncio.run(_run())


def test_enter_does_not_insert_newline(tmp_path):
    async def _run():
        app = make_app(tmp_path)
        app._handle_command = lambda command: None
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            area = app.query_one("#input")
            area.focus()
            await pilot.pause()
            await pilot.press("a")
            await pilot.press("enter")
            await pilot.pause()
            return area.text

    assert asyncio.run(_run()) == ""


def test_shift_enter_creates_newline(tmp_path):
    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            area = app.query_one("#input")
            area.focus()
            await pilot.pause()
            for ch in "hi":
                await pilot.press(ch)
            await pilot.press("shift+enter")
            await pilot.pause()
            return area.text

    assert asyncio.run(_run()) == "hi\n"


def test_shift_enter_does_not_submit(tmp_path):
    async def _run():
        app = make_app(tmp_path)
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            area = app.query_one("#input")
            area.focus()
            await pilot.pause()
            await pilot.press("a")
            await pilot.press("shift+enter")
            await pilot.pause()
            return dispatched

    assert asyncio.run(_run()) == []


def test_enter_run_and_shift_enter_hints_visible(tmp_path):
    # RQ-TUI-021/030/034: the visible UI communicates "Enter Run" and
    # "Shift+Enter New line" through the binding hints rendered in the footer.
    async def check(app, pilot):
        area = app.query_one("#input")
        area.focus()
        await pilot.pause()
        active = {
            key: (value.binding.action, value.binding.description)
            for key, value in app.active_bindings.items()
        }
        return (
            active.get("enter") == ("submit", "Enter Run")
            and active.get("shift+enter") == ("insert_newline", "New line")
        )

    assert mounted(tmp_path, check)


def test_ctrl_enter_is_not_a_submit_mechanism(tmp_path):
    # Ctrl+Enter must not be the submission mechanism (RQ-TUI-021/030): no
    # global binding declares it and typing it does not dispatch.
    assert not any(
        b.key == "ctrl+enter" for b in AdaSenseiTUI.BINDINGS
    )
    from ada_sensei.cli.tui.bindings import BINDINGS

    assert not any(b.key == "ctrl+enter" for b in BINDINGS)

    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        area = app.query_one("#input")
        area.text = "why does compose fail?"
        await pilot.press("ctrl+enter")
        await pilot.pause()
        assert dispatched == []
        return True

    assert mounted(tmp_path, check)


def test_clear_after_submission(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        area = app.query_one("#input")
        area.text = "some text"
        app.action_submit()
        return area.text == ""

    assert mounted(tmp_path, check)


def test_focus_restored_after_submission(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        area = app.query_one("#input")
        area.text = "some text"
        area.blur()
        await pilot.pause()
        app.action_submit()
        await pilot.pause()
        return app.focused is area

    assert mounted(tmp_path, check)


def test_focus_restored_after_completion(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        area.blur()
        await pilot.pause()
        app._set_busy(False, "Ready")
        app._focus_input()
        await pilot.pause()
        return app.focused is area

    assert mounted(tmp_path, check)


def test_focus_restored_after_error(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        area.blur()
        await pilot.pause()
        app._set_busy(False, "Error")
        app._focus_input()
        await pilot.pause()
        return app.focused is area

    assert mounted(tmp_path, check)


def test_focus_restored_after_cancellation(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        area.blur()
        await pilot.pause()
        app.action_cancel_operation()
        await pilot.pause()
        return app.focused is area

    assert mounted(tmp_path, check)


def test_input_not_disabled_after_worker(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input")
        app._set_busy(False, "Ready")
        return area.disabled is False

    assert mounted(tmp_path, check)


def test_global_bindings_do_not_consume_printable_keys(tmp_path):
    # No global shortcut may be a single printable character (which would steal
    # ordinary typing); only chorded/function shortcuts are allowed.
    single_printable = [
        b.key for b in AdaSenseiTUI.BINDINGS if len(b.key) == 1 and b.key.isprintable()
    ]
    assert single_printable == []


def test_multiline_preserved_on_routing(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        area = app.query_one("#input")
        area.text = "first\nsecond\nthird"
        app.action_submit()
        assert area.text == ""
        assert dispatched[0].question == "first\nsecond\nthird"
        return True

    assert mounted(tmp_path, check)


def test_slash_command_bypasses_action_routing(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        app.ui_state.action = "examples"
        area = app.query_one("#input")
        area.text = "/ask what is state?"
        app.action_submit()
        assert isinstance(dispatched[0], AskCommand)
        assert dispatched[0].question == "what is state?"
        return True

    assert mounted(tmp_path, check)


def test_action_routing_practice_and_examples(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        app.ui_state.action = "practice"
        area = app.query_one("#input")
        area.text = "compose-state"
        app.action_submit()
        assert isinstance(dispatched[0], PracticeCommand)
        assert dispatched[0].topic == "compose-state"

        app.ui_state.action = "examples"
        area.text = "ViewModel"
        app.action_submit()
        assert isinstance(dispatched[1], ExamplesCommand)
        assert dispatched[1].topic == "ViewModel"
        return True

    assert mounted(tmp_path, check)