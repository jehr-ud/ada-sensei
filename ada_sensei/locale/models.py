"""Locale preference model (spec 0010)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

SUPPORTED_LOCALES: tuple[str, ...] = ("es-CO", "en-US")
FALLBACK_LOCALE = "en-US"


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


__all__ = ["FALLBACK_LOCALE", "LocalePreference", "SUPPORTED_LOCALES"]
