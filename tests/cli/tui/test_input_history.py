"""TUI input prompt history navigation (RQ-TUI-039).

Session-local Up/Down recall of non-empty submitted inputs: reverse-order
navigation, draft restoration, multiline cursor compatibility, edit-before-
submit, bounded storage, and no domain-state side effects. History lives in
presentation state only (``InputHistory``); the router and agents are untouched.
"""

from __future__ import annotations

import asyncio

from ada_sensei.cli.commands import AskCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.history import MAX_HISTORY_ENTRIES, InputHistory
from ada_sensei.cli.tui.widgets import PromptArea
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


def make_app(tmp_path) -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    return AdaSenseiTUI(router=router)


def mounted(tmp_path, fn, name="Ada"):
    """Run async ``fn(app, pilot)`` as an onboarded student with locale set."""

    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, name)
            seed_learning_profile(tmp_path, name)
            app._resolve_pending_name(name)
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def _submit(app, text: str) -> None:
    area = app.query_one("#input", PromptArea)
    area.text = text
    app.action_submit()


# ---------------------------------------------------------------------------
# InputHistory unit behavior
# ---------------------------------------------------------------------------


def test_record_ignores_blank_and_dedupes_consecutive():
    history = InputHistory()
    assert history.record("   ") is False
    assert history.record("") is False
    assert history.entries == []
    assert history.record("hello") is True
    assert history.record("hello") is False  # consecutive duplicate
    assert history.entries == ["hello"]
    assert history.record("hello world") is True
    assert history.entries == ["hello", "hello world"]


def test_history_is_bounded_and_drops_oldest():
    history = InputHistory(max_entries=3)
    for i in range(5):
        history.record(f"prompt {i}")
    assert history.entries == ["prompt 2", "prompt 3", "prompt 4"]


def test_default_bound_is_documented():
    assert MAX_HISTORY_ENTRIES == 100
    assert InputHistory().max_entries == 100


def test_navigation_order_and_draft_restoration():
    history = InputHistory()
    assert history.begin("draft") is None  # empty history: stays inactive
    assert history.browsing is False
    for text in ("first", "second", "third"):
        history.record(text)
    assert history.begin("my draft") == "third"
    assert history.browsing is True
    assert history.older() == "second"
    assert history.older() == "first"
    assert history.older() == "first"  # stops at the oldest
    assert history.newer() == "second"
    assert history.newer() == "third"
    assert history.newer() == "my draft"  # past newest restores draft
    assert history.browsing is False


def test_record_exits_navigation():
    history = InputHistory()
    history.record("a")
    history.begin("")
    assert history.browsing is True
    history.record("b")
    assert history.browsing is False
    assert history.entries == ["a", "b"]


# ---------------------------------------------------------------------------
# TUI behavior through the real TextArea widget
# ---------------------------------------------------------------------------


def test_up_recalls_newest_without_executing(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        _submit(app, "Explain Compose state")
        await pilot.pause()
        dispatched.clear()  # setup submission done; recall must add nothing
        area = app.query_one("#input", PromptArea)
        area.text = ""
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "Explain Compose state"
        assert dispatched == []  # recall never dispatches
        assert app.ui_state.action == "ask"  # selector untouched
        return True

    assert mounted(tmp_path, check)


def test_repeated_up_recalls_older_entries_in_order(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        for text in ("first", "second", "third"):
            _submit(app, text)
            await pilot.pause()
        dispatched.clear()  # setup submissions done; recall must add nothing
        area = app.query_one("#input", PromptArea)
        area.text = ""
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "third"
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "second"
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "first"
        await pilot.press("up")  # stops at the oldest
        await pilot.pause()
        assert area.text == "first"
        assert dispatched == []
        return True

    assert mounted(tmp_path, check)


def test_down_recalls_newer_entries(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        for text in ("first", "second"):
            _submit(app, text)
            await pilot.pause()
        area = app.query_one("#input", PromptArea)
        area.text = ""
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "first"
        await pilot.press("down")
        await pilot.pause()
        assert area.text == "second"
        return True

    assert mounted(tmp_path, check)


def test_down_past_newest_restores_original_draft(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        _submit(app, "saved prompt")
        await pilot.pause()
        area = app.query_one("#input", PromptArea)
        area.text = "unsent draft"
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "saved prompt"
        await pilot.press("down")
        await pilot.pause()
        assert area.text == "unsent draft"  # draft restored, not overwritten
        assert app.input_history.browsing is False
        # Browsing ended: further Down keeps normal behavior.
        await pilot.press("down")
        await pilot.pause()
        assert area.text == "unsent draft"
        return True

    assert mounted(tmp_path, check)


def test_up_inside_multiline_moves_cursor_normally(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        _submit(app, "older prompt")
        await pilot.pause()
        area = app.query_one("#input", PromptArea)
        area.text = "line one\nline two\nline three"
        area.move_cursor((1, 0))  # middle line: not the first-line boundary
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "line one\nline two\nline three"  # no recall
        assert area.cursor_location[0] == 0  # caret moved up normally
        assert app.input_history.browsing is False
        return True

    assert mounted(tmp_path, check)


def test_down_inside_multiline_moves_cursor_normally(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        _submit(app, "older prompt")
        await pilot.pause()
        area = app.query_one("#input", PromptArea)
        area.text = "line one\nline two\nline three"
        area.move_cursor((0, 0))  # first line: not the last-line boundary
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert area.text == "line one\nline two\nline three"  # no recall
        assert area.cursor_location[0] == 1  # caret moved down normally
        assert app.input_history.browsing is False
        return True

    assert mounted(tmp_path, check)


def test_recalled_prompt_editable_and_executes_only_on_enter(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        _submit(app, "original question")
        await pilot.pause()
        dispatched.clear()  # setup submission done; recall must add nothing
        area = app.query_one("#input", PromptArea)
        area.text = ""
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "original question"
        assert dispatched == []  # recall alone never executes
        await pilot.press("x")  # edit the recall; deterministic exit
        await pilot.pause()
        assert area.text == "original questionx"
        assert app.input_history.browsing is False
        assert dispatched == []
        await pilot.press("enter")  # explicit Enter submits the edit
        await pilot.pause()
        assert len(dispatched) == 1
        assert isinstance(dispatched[0], AskCommand)
        assert dispatched[0].question == "original questionx"
        assert "original questionx" in app.input_history.entries
        return True

    assert mounted(tmp_path, check)


def test_blank_and_system_messages_not_recorded(tmp_path):
    async def check(app, pilot):
        app._handle_command = lambda command: None
        _submit(app, "kept prompt")
        await pilot.pause()
        area = app.query_one("#input", PromptArea)
        area.text = "   "
        app.action_submit()  # whitespace-only: ignored
        await pilot.pause()
        assert app.input_history.entries == ["kept prompt"]
        app._emit("assistant response")
        app._emit_kind("assistant", "system notice")
        assert app.input_history.entries == ["kept prompt"]
        return True

    assert mounted(tmp_path, check)


def test_shift_enter_inserts_newline_and_exits_browsing(tmp_path):
    async def check(app, pilot):
        dispatched = []
        app._handle_command = lambda command: dispatched.append(command)
        _submit(app, "saved")
        await pilot.pause()
        dispatched.clear()  # setup submission done; recall must add nothing
        area = app.query_one("#input", PromptArea)
        area.text = ""
        await pilot.press("up")
        await pilot.pause()
        assert area.text == "saved"
        await pilot.press("shift+enter")
        await pilot.pause()
        assert dispatched == []  # newline never submits
        assert "\n" in area.text  # newline inserted after the recall
        assert app.input_history.browsing is False
        return True

    assert mounted(tmp_path, check)


def test_history_never_touches_domain_state(tmp_path):
    async def check(app, pilot):
        from ada_sensei.learning.stores import LearningProfileStore

        app._handle_command = lambda command: None
        _submit(app, "some question")
        await pilot.pause()
        area = app.query_one("#input", PromptArea)
        area.text = ""
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        # Navigation alone dispatches nothing and persists nothing.
        assert (
            LearningProfileStore(str(tmp_path)).get("Ada").current_stage_id
            == "kotlin-fundamentals"
        )
        assert app.router.last_score() is None
        assert app.ui_state.action == "ask"
        return True

    assert mounted(tmp_path, check)
