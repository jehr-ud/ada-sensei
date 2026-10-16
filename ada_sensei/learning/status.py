"""Resolve the student's current learning stage for GUI display.

Read-only helper: loads the persisted ``LearningProfile`` for the student,
loads the locale-specific stage catalog, and returns a display-ready status.
Never advances the stage, never infers mastery, and never writes state.
A pending (unpersisted) evaluation therefore cannot change the displayed stage:
only a persisted ``LearningProfile.current_stage_id`` update changes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..learning.catalog import LearningCatalogLoader
from ..locale.models import FALLBACK_LOCALE


@dataclass(frozen=True)
class LearningStageStatus:
    state: str  # "active" | "not_started" | "unknown"
    stage_id: str | None = None
    stage_number: int | None = None
    stage_name: str | None = None
    objective: str | None = None
    locale: str = FALLBACK_LOCALE

    def display(self, locale: str | None = None) -> str:
        """Localized one-line status, e.g. ``Etapa actual: 5 — Nombre``."""
        from ..locale.ui_strings import get_ui_string

        loc = locale or self.locale
        if self.state == "not_started":
            return get_ui_string("stage_not_started", loc)
        if self.state != "active" or self.stage_number is None or not self.stage_name:
            return get_ui_string("stage_unknown", loc)
        prefix = get_ui_string("stage_current", loc)
        return f"{prefix}: {self.stage_number} — {self.stage_name}"


def resolve_learning_stage(
    data_dir: str | Path,
    student_id: str | None,
    locale: str | None,
    *,
    catalog_loader: LearningCatalogLoader | None = None,
) -> LearningStageStatus:
    """Resolve the current stage from persisted progress and the catalog.

    - Missing/blank student or missing profile → ``not_started``.
    - Invalid stage reference or catalog errors → ``unknown`` (never crash).
    - Locale falls back to ``en-US`` for catalog loading when needed.
    """
    from ..learning.stores import LearningProfileStore

    loc = locale if locale in ("es-CO", "en-US") else FALLBACK_LOCALE
    if not student_id or not str(student_id).strip():
        return LearningStageStatus(state="not_started", locale=loc)
    try:
        store = LearningProfileStore(data_dir)
        profile = store.get(student_id)
    except Exception:  # noqa: BLE001 - GUI must degrade gracefully
        return LearningStageStatus(state="unknown", locale=loc)
    if profile is None or not profile.current_stage_id:
        return LearningStageStatus(state="not_started", locale=loc)
    loader = catalog_loader or LearningCatalogLoader()
    catalog = None
    used_locale = loc
    try:
        catalog = loader.load_catalog(loc)
    except Exception:  # noqa: BLE001 - try deterministic fallback
        try:
            catalog = loader.load_catalog(FALLBACK_LOCALE)
            used_locale = FALLBACK_LOCALE
        except Exception:  # noqa: BLE001
            return LearningStageStatus(state="unknown", locale=loc)
    assert catalog is not None
    for stage in catalog.stages:
        if stage.id == profile.current_stage_id:
            return LearningStageStatus(
                state="active",
                stage_id=stage.id,
                stage_number=stage.number,
                stage_name=stage.title,
                objective=stage.objective,
                locale=used_locale,
            )
    return LearningStageStatus(state="unknown", locale=loc)


__all__ = ["LearningStageStatus", "resolve_learning_stage"]
