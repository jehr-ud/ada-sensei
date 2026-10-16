"""Language-selection state machine (spec 0010, RQ-LNG-004/005).

Framework-independent cursor model for the dedicated language list: exactly
the supported locales from the single definition in ``locale.models``, a
visible focus index, wrap-around Up/Down movement, and explicit confirm /
cancel. The TUI widget renders this state; persistence and UI refresh stay in
the existing router/TUI paths. No translated label is ever used as an ID.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import FALLBACK_LOCALE, LOCALE_OPTIONS, SUPPORTED_LOCALES


@dataclass
class LanguageSelection:
    """Cursor state over the supported language options."""

    options: tuple[tuple[str, str], ...] = LOCALE_OPTIONS
    index: int = 0
    cancelled: bool = False
    confirmed: str | None = None

    def __post_init__(self) -> None:
        if not self.options:
            raise ValueError("language selection requires at least one option")
        self.index %= len(self.options)

    @classmethod
    def with_focus(
        cls, locale: str | None, *, default: str = FALLBACK_LOCALE
    ) -> LanguageSelection:
        """Focus the saved locale when known, otherwise the default.

        First-run callers pass ``locale=None`` and still must confirm
        explicitly: focusing a default never counts as a student choice.
        """
        options = LOCALE_OPTIONS
        codes = [code for code, _ in options]
        focus = locale if locale in codes else default
        return cls(options=options, index=codes.index(focus))

    def move_up(self) -> str:
        self.index = (self.index - 1) % len(self.options)
        return self.focused_locale

    def move_down(self) -> str:
        self.index = (self.index + 1) % len(self.options)
        return self.focused_locale

    @property
    def focused_locale(self) -> str:
        return self.options[self.index][0]

    @property
    def focused_label(self) -> str:
        return self.options[self.index][1]

    def confirm(self) -> str:
        """Explicit confirmation of the focused locale (stable ID)."""
        self.confirmed = self.focused_locale
        return self.confirmed

    def cancel(self) -> None:
        self.cancelled = True


def parse_language_choice(text: str | None) -> str | None:
    """Map typed input (slash args, legacy prompts) to a stable locale ID.

    Returns the locale code or ``None`` when the input selects nothing.
    Display labels map back to codes here only; execution paths always carry
    the returned code.
    """
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return None
    for code in SUPPORTED_LOCALES:
        if cleaned == code.lower():
            return code
    mapping = {
        "1": "es-CO",
        "español": "es-CO",
        "espanol": "es-CO",
        "spanish": "es-CO",
        "2": "en-US",
        "english": "en-US",
        "inglés": "en-US",
        "ingles": "en-US",
    }
    return mapping.get(cleaned)


__all__ = ["LanguageSelection", "parse_language_choice"]
