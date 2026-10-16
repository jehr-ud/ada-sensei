"""Interactive language-selection list (spec 0010, RQ-LNG-004/005/006/007).

Verifies through the real TUI: opening via `Change language`, visible cursor
and key hints, Up/Down navigation, Enter confirmation with immediate UI
refresh, Esc/q cancellation, saved-locale focus, restart persistence,
learning-state preservation, and first-run ordering.
"""

from __future__ import annotations

import asyncio

from ada_sensei.cli.commands import LanguageCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import ActionSelector, LanguageList, SessionFooter
from ada_sensei.config import Config
from ada_sensei.learning.stores import LearningProfileStore
from ada_sensei.llm.base import LLMClient
from ada_sensei.locale.service import LocaleService
from ada_sensei.locale.store import LocalePreferenceStore

from conftest import seed_learning_profile


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


def _saved(tmp_path) -> str | None:
    return LocaleService(LocalePreferenceStore(str(tmp_path))).get_or_prompt_locale(
        "Ada"
    )


def _open(app, locale: str = "en-US", stage: str = "kotlin-fundamentals") -> None:
    """Seed a saved locale and open the list as an onboarded student."""
    app.router.context.set_student("Ada")
    app.router.dispatch(LanguageCommand(locale=locale))
    seed_learning_profile(app.router.config.resolved_data_dir, "Ada", stage_id=stage)
    app._handle_command(LanguageCommand(locale=None))


# -- RQ-LNG-004/005: dedicated list, cursor, hints --------------------------------


def test_change_language_opens_list_with_options_and_hints(tmp_path):
    async def check(app, pilot):
        _open(app)
        assert app._pending_language is True
        widget = app.query_one("#language-list", LanguageList)
        assert widget.is_open
        assert [code for code, _ in widget.selection.options] == [
            "es-CO",
            "en-US",
        ]
        text = str(widget.renderable)
        assert "Español" in text and "English" in text
        assert ">" in text  # visible cursor marker
        assert "Enter" in text and ("Esc" in text or "esc" in text.lower())
        return True

    assert mounted(tmp_path, check)


def test_cursor_movement_changes_focus(tmp_path):
    async def check(app, pilot):
        _open(app, locale="es-CO")
        assert app._language_selection.focused_locale == "es-CO"
        await pilot.press("down")
        await pilot.pause()
        assert app._language_selection.focused_locale == "en-US"
        await pilot.press("up")
        await pilot.pause()
        assert app._language_selection.focused_locale == "es-CO"
        return True

    assert mounted(tmp_path, check)


def test_enter_confirms_focused_locale_and_refreshes(tmp_path):
    async def check(app, pilot):
        _open(app, locale="en-US")
        seed_learning_profile(tmp_path, "Ada")
        await pilot.press("up")  # focus Español
        await pilot.pause()
        assert app._language_selection.focused_locale == "es-CO"
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()
        assert _saved(tmp_path) == "es-CO"
        assert app._pending_language is False
        # Confirmation arrives in the newly selected language.
        assert any("Español" in m for m in app.ui_state.messages)
        # Visible UI refreshed immediately: selector labels, footer, hints.
        footer = str(app.query_one("#session-footer", SessionFooter).renderable)
        assert "Lang: es-CO" in footer
        return True

    assert mounted(tmp_path, check)


def test_escape_cancels_without_changing_locale(tmp_path):
    async def check(app, pilot):
        _open(app, locale="en-US")
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app._pending_language is False
        assert _saved(tmp_path) == "en-US"
        widget = app.query_one("#language-list", LanguageList)
        assert not widget.is_open
        return True

    assert mounted(tmp_path, check)


def test_q_cancels_without_changing_locale(tmp_path):
    async def check(app, pilot):
        _open(app, locale="es-CO")
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        assert _saved(tmp_path) == "es-CO"
        assert app._pending_language is False
        return True

    assert mounted(tmp_path, check)


def test_saved_locale_focused_on_reentry(tmp_path):
    async def check(app, pilot):
        _open(app, locale="es-CO")
        assert app._language_selection.focused_locale == "es-CO"
        app._cancel_language_flow()
        app._handle_command(LanguageCommand(locale=None))
        assert app._language_selection.focused_locale == "es-CO"
        return True

    assert mounted(tmp_path, check)


# -- RQ-LNG-003/006/007: persistence, refresh, preservation ------------------------


def test_restart_restores_chosen_locale(tmp_path):
    async def check(app, pilot):
        _open(app, locale="en-US")
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()
        assert _saved(tmp_path) == "es-CO"
        return True

    assert mounted(tmp_path, check)
    second = make_app(tmp_path)
    second.router.context.set_student("Ada")
    assert second.router.current_locale() == "es-CO"
    assert second.router.saved_locale() == "es-CO"


def test_learning_state_unchanged_by_language_switch(tmp_path):
    async def check(app, pilot):
        app.router.context.set_student("Ada")
        before_score = app.router.last_score()
        _open(app, locale="en-US", stage="state-basic-architecture")
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()
        profile = LearningProfileStore(str(tmp_path)).get("Ada")
        assert profile.current_stage_id == "state-basic-architecture"
        assert profile.mastered_stages == []
        assert app.router.last_score() == before_score
        assert _saved(tmp_path) == "es-CO"
        return True

    assert mounted(tmp_path, check)


def test_action_labels_use_stable_ids_across_locales(tmp_path):
    from ada_sensei.cli.action_registry import action_ids
    from ada_sensei.cli.tui.app import localized_action_options

    assert [v for _, v in localized_action_options("es-CO")] == list(action_ids())
    assert [v for _, v in localized_action_options("en-US")] == list(action_ids())


# -- RQ-LNG-002: first-run ordering -------------------------------------------------


def test_first_run_opens_language_list_before_onboarding(tmp_path):
    async def check(app, pilot):
        # Fresh mount with no saved locale and no profile: language gate first.
        assert app._pending_language is True
        assert app._pending_onboarding is False
        widget = app.query_one("#language-list", LanguageList)
        assert widget.is_open
        return True

    assert mounted(tmp_path, check)


def test_first_run_cancel_keeps_onboarding_blocked(tmp_path):
    async def check(app, pilot):
        assert app._pending_language is True
        await pilot.press("escape")
        await pilot.pause()
        # Still no saved locale: the gate stays open, onboarding blocked.
        assert _saved(tmp_path) is None
        assert app._pending_language is True
        assert app._pending_onboarding is False
        assert LearningProfileStore(str(tmp_path)).get("Ada") is None
        return True

    assert mounted(tmp_path, check)


def test_first_run_confirm_proceeds_to_onboarding(tmp_path):
    async def check(app, pilot):
        assert app._pending_language is True
        await pilot.press("enter")  # confirm defaulted en-US explicitly
        await pilot.pause()
        await pilot.pause()
        assert _saved(tmp_path) == "en-US"
        assert app._pending_language is False
        assert app._pending_onboarding is True
        joined = "\n".join(app.ui_state.messages)
        assert "Learning stages:" in joined
        return True

    assert mounted(tmp_path, check)


def test_selector_and_welcome_share_the_same_list(tmp_path):
    """RQ-LNG-004b: both entry points render the same options, cursor, hints."""
    from ada_sensei.locale.models import LOCALE_OPTIONS

    async def check(app, pilot):
        # First-run (welcome) list is already open after mount.
        welcome = app.query_one("#language-list", LanguageList)
        assert welcome.is_open
        welcome_options = [code for code, _ in welcome.selection.options]
        assert welcome_options == [code for code, _ in LOCALE_OPTIONS]
        welcome_text = str(welcome.renderable)

        # Confirm to close it, then reopen from the action selector.
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()
        app._handle_command(LanguageCommand(locale=None))
        await pilot.pause()
        selector = app.query_one("#language-list", LanguageList)
        assert selector.is_open
        assert [code for code, _ in selector.selection.options] == welcome_options
        assert str(selector.renderable) == welcome_text
        return True

    assert mounted(tmp_path, check)


def mounted_seeded(tmp_path, fn, locale: str = "en-US"):
    """Mount with locale+profile seeded before name resolution (no gates)."""

    async def _run():
        from conftest import seed_saved_locale

        app = make_app(tmp_path)
        seed_saved_locale(tmp_path, "Ada", locale=locale)
        seed_learning_profile(tmp_path, "Ada")
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def test_selector_enter_opens_same_list(tmp_path):
    """RQ-LNG-015: Enter on the focused selector opens LanguageList."""
    from ada_sensei.locale.models import LOCALE_OPTIONS
    from textual.widgets import Select

    async def check(app, pilot):
        assert app._pending_language is False
        sel = app.query_one("#action-select", Select)
        assert isinstance(sel, ActionSelector)
        sel.value = "language"
        await pilot.pause()
        sel.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app._pending_language is True
        widget = app.query_one("#language-list", LanguageList)
        assert widget.is_open
        assert [code for code, _ in widget.selection.options] == [
            code for code, _ in LOCALE_OPTIONS
        ]
        text = str(widget.renderable)
        assert "Select language / Selecciona el idioma" in text
        assert "Español" in text and "English" in text
        assert widget.selection.focused_locale == "en-US"  # saved focused
        return True

    assert mounted_seeded(tmp_path, check, locale="en-US")


def test_selector_enter_matches_stable_id_not_label(tmp_path):
    """RQ-LNG-015: interception keys off `language`, shown label is Español UI."""
    from textual.widgets import Select

    async def check(app, pilot):
        app.router.context.set_student("Ada")
        app._refresh_selector_labels()
        await pilot.pause()
        sel = app.query_one("#action-select", Select)
        labels = [str(option[0]) for option in sel._options]
        assert any("dioma" in label for label in labels)  # localized visible
        sel.value = "language"
        await pilot.pause()
        sel.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.query_one("#language-list", LanguageList).is_open
        return True

    assert mounted_seeded(tmp_path, check, locale="es-CO")


def test_selector_enter_other_action_keeps_native_behavior(tmp_path):
    """Enter on a non-language action must not open the language list."""
    from textual.widgets import Select

    async def check(app, pilot):
        sel = app.query_one("#action-select", Select)
        sel.value = "ask"
        await pilot.pause()
        sel.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app._pending_language is False
        assert not app.query_one("#language-list", LanguageList).is_open
        return True

    assert mounted_seeded(tmp_path, check, locale="en-US")


def test_selector_enter_full_keyboard_confirm(tmp_path):
    """End-to-end via keys only: selector Enter, Up, Enter persists es-CO."""
    from textual.widgets import Select

    async def check(app, pilot):
        sel = app.query_one("#action-select", Select)
        sel.value = "language"
        await pilot.pause()
        sel.focus()
        await pilot.pause()
        await pilot.press("enter")  # opens list
        await pilot.pause()
        await pilot.press("up")  # en-US -> es-CO
        await pilot.pause()
        await pilot.press("enter")  # confirm
        await pilot.pause()
        await pilot.pause()
        assert _saved(tmp_path) == "es-CO"
        assert app._pending_language is False
        assert not app.query_one("#language-list", LanguageList).is_open
        profile = LearningProfileStore(str(tmp_path)).get("Ada")
        assert profile.current_stage_id == "kotlin-fundamentals"
        assert profile.mastered_stages == []
        return True

    assert mounted_seeded(tmp_path, check, locale="en-US")


def test_selector_open_sends_nothing_to_teacher(tmp_path):
    """Opening/confirming dispatches no free text to TeacherAgent."""
    from textual.widgets import Select

    async def check(app, pilot):
        seen = []
        original = app.router.dispatch

        def spy(command):
            seen.append(type(command).__name__)
            return original(command)

        app.router.dispatch = spy
        sel = app.query_one("#action-select", Select)
        sel.value = "language"
        await pilot.pause()
        sel.focus()
        await pilot.pause()
        await pilot.press("enter")  # opens list: no dispatch
        await pilot.pause()
        await pilot.press("escape")  # cancel: no dispatch
        await pilot.pause()
        assert seen == []
        assert _saved(tmp_path) == "en-US"
        return True

    assert mounted_seeded(tmp_path, check, locale="en-US")
