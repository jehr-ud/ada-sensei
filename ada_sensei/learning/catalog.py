"""Load and validate learning catalog, rubrics, and policy from config/ (spec 008)."""
from __future__ import annotations

import json
from pathlib import Path

from .models import (
    ProgressionPolicy,
    RubricCatalog,
    StageCatalog,
    StageRubric,
)

# Two levels up from ada_sensei/learning/ → repo root, then config/
_DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

_LOCALE_SUFFIX: dict[str, str] = {
    "en-US": "en",
    "es-CO": "es",
}


class ConfigLoadError(ValueError):
    """Raised when a config file is missing, invalid JSON, or fails validation."""


class LearningCatalogLoader:
    """Load and validate catalog / rubric / policy from the config directory."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or _DEFAULT_CONFIG_DIR

    # -- public loaders ---------------------------------------------------

    def load_catalog(self, locale: str) -> StageCatalog:
        suffix = self._suffix(locale)
        path = self.config_dir / f"stages.{suffix}.json"
        data = self._read_json(path)
        try:
            return StageCatalog.model_validate(data)
        except Exception as exc:
            raise ConfigLoadError(f"invalid catalog {path}: {exc}") from exc

    def load_rubrics(self, locale: str) -> RubricCatalog:
        suffix = self._suffix(locale)
        path = self.config_dir / f"stage-rubrics.{suffix}.json"
        data = self._read_json(path)
        try:
            return RubricCatalog.model_validate(data)
        except Exception as exc:
            raise ConfigLoadError(f"invalid rubrics {path}: {exc}") from exc

    def load_policy(self, locale: str) -> ProgressionPolicy:
        suffix = self._suffix(locale)
        path = self.config_dir / f"progression-policy.{suffix}.json"
        data = self._read_json(path)
        try:
            return ProgressionPolicy.model_validate(data)
        except Exception as exc:
            raise ConfigLoadError(f"invalid policy {path}: {exc}") from exc

    def get_rubric_for_stage(
        self, stage_id: str, rubric_catalog: RubricCatalog
    ) -> StageRubric:
        for rubric in rubric_catalog.rubrics:
            if rubric.stage_id == stage_id:
                return rubric
        raise ConfigLoadError(f"no rubric found for stage_id {stage_id!r}")

    # -- cross-locale validation ------------------------------------------

    def validate_cross_locale_consistency(self) -> list[str]:
        """Return diagnostic messages if en-US and es-CO configs diverge on IDs/weights/gates."""
        diagnostics: list[str] = []
        try:
            cat_en = self.load_catalog("en-US")
            cat_es = self.load_catalog("es-CO")
            rub_en = self.load_rubrics("en-US")
            rub_es = self.load_rubrics("es-CO")
            pol_en = self.load_policy("en-US")
            pol_es = self.load_policy("es-CO")
        except ConfigLoadError as exc:
            return [f"load error: {exc}"]

        # Stage IDs
        ids_en = {s.id for s in cat_en.stages}
        ids_es = {s.id for s in cat_es.stages}
        if ids_en != ids_es:
            diagnostics.append(
                f"stage IDs differ: en-only={ids_en - ids_es}, es-only={ids_es - ids_en}"
            )

        # Rubric IDs
        rub_ids_en = {r.id for r in rub_en.rubrics}
        rub_ids_es = {r.id for r in rub_es.rubrics}
        if rub_ids_en != rub_ids_es:
            diagnostics.append(
                f"rubric IDs differ: en-only={rub_ids_en - rub_ids_es}, "
                f"es-only={rub_ids_es - rub_ids_en}"
            )

        # Criterion IDs per rubric
        rub_map_en = {r.id: r for r in rub_en.rubrics}
        rub_map_es = {r.id: r for r in rub_es.rubrics}
        for rid in rub_ids_en & rub_ids_es:
            crit_en = {
                c.id
                for d in rub_map_en[rid].dimensions
                for c in d.criteria
            }
            crit_es = {
                c.id
                for d in rub_map_es[rid].dimensions
                for c in d.criteria
            }
            if crit_en != crit_es:
                diagnostics.append(
                    f"rubric {rid!r} criterion IDs differ: "
                    f"en-only={crit_en - crit_es}, es-only={crit_es - crit_en}"
                )
            # Weights
            weights_en = {d.id: d.weight for d in rub_map_en[rid].dimensions}
            weights_es = {d.id: d.weight for d in rub_map_es[rid].dimensions}
            if weights_en != weights_es:
                diagnostics.append(
                    f"rubric {rid!r} dimension weights differ: en={weights_en} es={weights_es}"
                )

        # Policy gates
        gates_en = pol_en.decision_gates
        gates_es = pol_es.decision_gates
        for attr in (
            "minimum_overall_score",
            "minimum_each_dimension_score",
            "minimum_critical_criterion_score",
        ):
            if getattr(gates_en, attr) != getattr(gates_es, attr):
                diagnostics.append(
                    f"decision_gates.{attr} differs: "
                    f"en={getattr(gates_en, attr)} es={getattr(gates_es, attr)}"
                )

        if not diagnostics:
            diagnostics.append("cross-locale consistency: OK")
        return diagnostics

    # -- helpers ----------------------------------------------------------

    def _suffix(self, locale: str) -> str:
        suffix = _LOCALE_SUFFIX.get(locale)
        if suffix is None:
            raise ConfigLoadError(
                f"unsupported locale {locale!r}; supported: {list(_LOCALE_SUFFIX)}"
            )
        return suffix

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            raise ConfigLoadError(f"config file not found: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigLoadError(f"invalid JSON in {path}: {exc}") from exc


__all__ = ["ConfigLoadError", "LearningCatalogLoader"]
