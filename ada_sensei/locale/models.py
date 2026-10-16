"""Locale preference model (spec 0010)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

SUPPORTED_LOCALES: tuple[str, ...] = ("es-CO", "en-US")
FALLBACK_LOCALE = "en-US"

#: Single display-label definition for the supported locales (spec 0010).
#: All UI components (selector lists, confirmations, help) derive visible
#: names from here; stable locale codes stay the internal identifiers and
#: translated labels are never used as IDs.
LOCALE_LABELS: dict[str, str] = {
    "es-CO": "Español",
    "en-US": "English",
}

#: Selectable options in presentation order: ``(locale_code, label)``.
LOCALE_OPTIONS: tuple[tuple[str, str], ...] = tuple(
    (code, LOCALE_LABELS[code]) for code in SUPPORTED_LOCALES
)


class LocalePreference(BaseModel):
    locale: str
    locale_source: Literal["student_selection", "configured_default", "migration"]
    updated_at: datetime

    @field_validator("locale")
    @classmethod
    def _validate_locale(cls, v: str) -> str:
        if v not in SUPPORTED_LOCALES:
            raise ValueError(
                f"unsupported locale {v!r}; supported: {list(SUPPORTED_LOCALES)}"
            )
        return v


__all__ = [
    "FALLBACK_LOCALE",
    "LOCALE_LABELS",
    "LOCALE_OPTIONS",
    "LocalePreference",
    "SUPPORTED_LOCALES",
]
