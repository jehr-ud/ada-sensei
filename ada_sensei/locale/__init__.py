"""Language selection and localization service (spec 0010-language-selection)."""
from __future__ import annotations

from .models import FALLBACK_LOCALE, SUPPORTED_LOCALES, LocalePreference
from .service import LocaleService
from .store import LocalePreferenceStore

__all__ = [
    "FALLBACK_LOCALE",
    "SUPPORTED_LOCALES",
    "LocaleFallbackDiagnostic",
    "LocalePreference",
    "LocaleService",
    "LocalePreferenceStore",
]
