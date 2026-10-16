"""Language-selection state machine unit tests (spec 0010, RQ-LNG-004/005/009).

Framework-free: cursor model, single locale definition, and typed-choice
parsing. TUI rendering and persistence are covered in
``tests/cli/tui/test_language_selection.py``.
"""

from __future__ import annotations

from ada_sensei.locale.models import (
    FALLBACK_LOCALE,
    LOCALE_LABELS,
    LOCALE_OPTIONS,
    SUPPORTED_LOCALES,
)
from ada_sensei.locale.selection import LanguageSelection, parse_language_choice


def test_single_definition_covers_supported_locales():
    assert SUPPORTED_LOCALES == ("es-CO", "en-US")
    assert [code for code, _ in LOCALE_OPTIONS] == list(SUPPORTED_LOCALES)
    assert LOCALE_LABELS == {"es-CO": "Español", "en-US": "English"}


def test_options_use_codes_as_ids_not_labels():
    selection = LanguageSelection.with_focus(None)
    assert selection.focused_locale in SUPPORTED_LOCALES
    assert selection.focused_locale != selection.focused_label


def test_focus_saved_locale_when_one_exists():
    assert LanguageSelection.with_focus("es-CO").focused_locale == "es-CO"
    assert LanguageSelection.with_focus("en-US").focused_locale == "en-US"


def test_first_run_focuses_default_without_choosing():
    selection = LanguageSelection.with_focus(None)
    assert selection.focused_locale == FALLBACK_LOCALE
    assert selection.confirmed is None  # focus is never a choice


def test_cursor_moves_with_wraparound():
    selection = LanguageSelection.with_focus("es-CO")
    assert selection.move_down() == "en-US"
    assert selection.move_down() == "es-CO"  # wraps
    assert selection.move_up() == "en-US"  # wraps
    assert selection.focused_label == "English"


def test_confirm_returns_stable_id():
    selection = LanguageSelection.with_focus(None)
    selection.move_up()
    assert selection.confirm() == "es-CO"
    assert selection.confirmed == "es-CO"


def test_cancel_marks_no_choice():
    selection = LanguageSelection.with_focus(None)
    selection.cancel()
    assert selection.cancelled is True
    assert selection.confirmed is None


def test_parse_typed_choices():
    assert parse_language_choice("es-CO") == "es-CO"
    assert parse_language_choice("EN-us") == "en-US"
    assert parse_language_choice("1") == "es-CO"
    assert parse_language_choice("2") == "en-US"
    assert parse_language_choice("Español") == "es-CO"
    assert parse_language_choice("english") == "en-US"
    assert parse_language_choice("") is None
    assert parse_language_choice(None) is None
    assert parse_language_choice("fr-FR") is None


def test_unknown_locale_never_focused():
    selection = LanguageSelection.with_focus("fr-FR")
    assert selection.focused_locale == FALLBACK_LOCALE
