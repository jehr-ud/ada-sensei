"""TUI tutoring flows: action guide, language flow, recommendations (spec 0011).

Covers REQ-002 (activation guidance), REQ-003 (parameter prompts), REQ-004
(language flow), REQ-005 (progress preservation), REQ-010 (no auto-execution).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ada_sensei.cli.commands import AskCommand, LanguageCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import ActionGuide
from ada_sensei.config import Config
from ada_sensei.learning.models import LearningProfile
from ada_sensei.learning.stores import LearningProfileStore
from ada_sensei.llm.base import LLMClient
from ada_sensei.locale.service import LocaleService
from ada_sensei.locale.store import LocalePreferenceStore


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


def _seed_profile(tmp_path, stage="kotlin-fundamentals"):
    now = datetime.now(tz=UTC)
    LearningProfileStore(str(tmp_path)).save(
        LearningProfile(
            student_id="Ada",
            catalog_id="android-learning-path",
            catalog_version="1.2.0",
            current_stage_id=stage,
            created_at=now,
            updated_at=now,
        )
    )


# -- REQ-002: activation guidance -------------------------------------------------


def test_guide_shows_description_and_activation_for_focused_action(tmp_path):
    async def check(app, pilot):
        guide = app.query_one("#action-guide", ActionGuide)
        text = str(guide.renderable)
        assert text, "guide must never be blank"
        assert "Enter" in text
        return True

    assert mounted(tmp_path, check)


def test_guide_updates_when_selection_changes(tmp_path):
    async def check(app, pilot):
        guide = app.query_one("#action-guide", ActionGuide)
        app.ui_state.action = "evaluate"
        app._refresh_guide()
        await pilot.pause()
        text = str(guide.renderable)
        assert text and "Enter" in text
        # Description differs per action.
        app.ui_state.action = "ask"
        app._refresh_guide()
        await pilot.pause()
        assert str(guide.renderable) != text
        return True

    assert mounted(tmp_path, check)


def test_guide_localized_on_locale_change(tmp_path):
    async def check(app, pilot):
        app.router.context.set_student("Ada")
        app.router.dispatch(LanguageCommand(locale="es-CO"))
        app._refresh_selector_labels()  # also refreshes the guide
        await pilot.pause()
        text = str(app.query_one("#action-guide", ActionGuide).renderable)
        assert "Enter" in text or "pulse" in text
        return True

    assert mounted(tmp_path, check)


# -- REQ-004: language-selection list -------------------------------------------


def test_language_without_choice_opens_list(tmp_path):
    from ada_sensei.cli.tui.widgets import LanguageList

    async def check(app, pilot):
        app._handle_command(LanguageCommand(locale=None))
        assert app._pending_language is True
        widget = app.query_one("#language-list", LanguageList)
        assert widget.is_open
        assert [code for code, _ in widget.selection.options] == [
            "es-CO",
            "en-US",
        ]
        text = str(widget.renderable)
        assert "Español" in text and "English" in text
        return True

    assert mounted(tmp_path, check)


def test_language_flow_choice_persists_and_confirms_in_new_locale(tmp_path):
    async def check(app, pilot):
        _seed_profile(tmp_path)
        app.router.context.set_student("Ada")
        app.router.dispatch(LanguageCommand(locale="en-US"))
        app._handle_command(LanguageCommand(locale=None))
        assert app._pending_language is True
        # Cursor focuses the saved locale; move to Español and confirm.
        app._language_selection.move_up()  # en-US (idx 1) -> es-CO (idx 0)
        assert app._language_selection.focused_locale == "es-CO"
        app._confirm_focused_language()
        await pilot.pause()
        assert app._pending_language is False
        svc = LocaleService(LocalePreferenceStore(str(tmp_path)))
        assert svc.get_or_prompt_locale("Ada") == "es-CO"
        assert any("Español" in m for m in app.ui_state.messages)
        # Progress preserved (REQ-005).
        assert (
            LearningProfileStore(str(tmp_path)).get("Ada").current_stage_id
            == "kotlin-fundamentals"
        )
        return True

    assert mounted(tmp_path, check)


def test_language_flow_cancel_leaves_locale_unchanged(tmp_path):
    async def check(app, pilot):
        app.router.context.set_student("Ada")
        app.router.dispatch(LanguageCommand(locale="en-US"))
        app._handle_command(LanguageCommand(locale=None))
        app._language_selection.move_down()
        app._cancel_language_flow()
        await pilot.pause()
        assert app._pending_language is False
        svc = LocaleService(LocalePreferenceStore(str(tmp_path)))
        assert svc.get_or_prompt_locale("Ada") == "en-US"
        return True

    assert mounted(tmp_path, check)


def test_language_flow_enter_with_focused_cursor(tmp_path):
    async def check(app, pilot):
        _seed_profile(tmp_path)
        app.router.context.set_student("Ada")
        app._handle_command(LanguageCommand(locale=None))
        # Default focus is en-US; Enter confirms without moving the cursor.
        assert app._language_selection.focused_locale == "en-US"
        app.action_submit()  # Enter while the list is open confirms
        await pilot.pause()
        svc = LocaleService(LocalePreferenceStore(str(tmp_path)))
        assert svc.get_or_prompt_locale("Ada") == "en-US"
        assert app._pending_language is False
        return True

    assert mounted(tmp_path, check)


def test_direct_locale_choice_skips_list(tmp_path):
    async def check(app, pilot):
        # First-run gate is open after mount with no saved locale.
        assert app._pending_language is True
        app.router.context.set_student("Ada")
        app._process_line("/language es-CO")
        await pilot.pause()
        await pilot.pause()
        svc = LocaleService(LocalePreferenceStore(str(tmp_path)))
        assert svc.get_or_prompt_locale("Ada") == "es-CO"
        assert app._pending_language is False
        return True

    assert mounted(tmp_path, check)


# -- REQ-003/010: prompts and no auto-execution ------------------------------------


def test_empty_ask_explains_required_input(tmp_path):
    async def check(app, pilot):
        reason = app._check_availability(AskCommand(question="   "))
        assert reason, "empty question must explain what to provide"
        return True

    assert mounted(tmp_path, check)


def test_recommendation_display_does_not_execute(tmp_path):
    async def check(app, pilot):
        from ada_sensei.cli.commands import MetaResult

        app._last_action_id = "ask"
        before = list(app.ui_state.messages)
        app._emit_recommendation(MetaResult(message="done"))
        assert len(app.ui_state.messages) > len(before)
        assert app._active_worker is None  # nothing dispatched
        assert app.ui_state.busy is False
        return True

    assert mounted(tmp_path, check)


def test_suggest_next_validated_against_registry(tmp_path):
    from ada_sensei.cli.action_registry import action_ids, check_availability

    async def check(app, pilot):
        from ada_sensei.cli.commands import MetaResult

        app._last_action_id = "ask"
        rec = app.router.suggest_next("ask", MetaResult(message="done"))
        assert rec is not None
        assert rec.action_id in action_ids()
        available, _ = check_availability(
            rec.action_id,
            project_path=str(tmp_path / "p"),
            exam_active=False,
            locale="en-US",
        )
        assert available
        return True

    assert mounted(tmp_path, check)
