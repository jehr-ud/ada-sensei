"""Locale resolution and config bundle loading (spec 0010)."""
from __future__ import annotations

from datetime import UTC, datetime

from ..learning.catalog import LearningCatalogLoader
from ..learning.models import ProgressionPolicy, RubricCatalog, StageCatalog
from .models import FALLBACK_LOCALE, SUPPORTED_LOCALES, LocalePreference
from .store import LocalePreferenceStore


class LocaleFallbackDiagnostic:
    """Emitted when a translation key is missing and the fallback is used."""

    def __init__(self, key: str, requested: str, fallback: str) -> None:
        self.key = key
        self.requested = requested
        self.fallback = fallback

    def __str__(self) -> str:
        return (
            f"[locale fallback] key={self.key!r} "
            f"requested={self.requested!r} -> fallback={self.fallback!r}"
        )


class LocaleService:
    """
    Resolve the locale for a student, load the matching config bundle,
    and propagate through the orchestration context.

    Follows spec 0010-language-selection invariants:
    - Locale never affects IDs, weights, scores, or progression decisions.
    - Missing translations use deterministic fallback (en-US by default).
    - Locale change does not reset learning data.
    """

    def __init__(
        self,
        store: LocalePreferenceStore,
        loader: LearningCatalogLoader | None = None,
    ) -> None:
        self._store = store
        self._loader = loader or LearningCatalogLoader()

    # -- locale preference ------------------------------------------------

    def get_or_prompt_locale(self, student_id: str) -> str | None:
        """Return saved locale, or None if first-run selection is needed."""
        pref = self._store.get(student_id)
        return pref.locale if pref is not None else None

    def set_locale(
        self,
        student_id: str,
        locale: str,
        source: str = "student_selection",
    ) -> LocalePreference:
        """Validate and persist locale. Does NOT modify any learning data."""
        validated = self.validate_locale(locale)
        pref = LocalePreference(
            locale=validated,
            locale_source=source,  # type: ignore[arg-type]
            updated_at=datetime.now(tz=UTC),
        )
        self._store.save(student_id, pref)
        return pref

    @staticmethod
    def validate_locale(locale: str) -> str:
        """Raise ValueError if locale is not supported."""
        if locale not in SUPPORTED_LOCALES:
            raise ValueError(
                f"unsupported locale {locale!r}; supported: {list(SUPPORTED_LOCALES)}"
            )
        return locale

    # -- config bundle ----------------------------------------------------

    def resolve_bundle(
        self, locale: str
    ) -> tuple[StageCatalog, RubricCatalog, ProgressionPolicy]:
        """Load the three config files for the given locale."""
        validated = self.validate_locale(locale)
        catalog = self._loader.load_catalog(validated)
        rubrics = self._loader.load_rubrics(validated)
        policy = self._loader.load_policy(validated)
        return catalog, rubrics, policy

    def resolve_bundle_with_fallback(
        self, locale: str
    ) -> tuple[StageCatalog, RubricCatalog, ProgressionPolicy, list[LocaleFallbackDiagnostic]]:
        """Load bundle; fall back to FALLBACK_LOCALE if locale files are missing."""
        diagnostics: list[LocaleFallbackDiagnostic] = []
        try:
            return (*self.resolve_bundle(locale), diagnostics)
        except Exception:  # noqa: BLE001
            diag = LocaleFallbackDiagnostic(
                key="config_bundle", requested=locale, fallback=FALLBACK_LOCALE
            )
            diagnostics.append(diag)
            return (*self.resolve_bundle(FALLBACK_LOCALE), diagnostics)


__all__ = ["LocaleFallbackDiagnostic", "LocaleService"]
