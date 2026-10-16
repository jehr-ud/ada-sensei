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
    """Load and validate catalog / rubric / policy from the config directory.

    Precedence and lifecycle (RQ-LRN-024): an explicit ``config_dir`` wins
    (used by tests and deployment overrides); otherwise the repository root
    ``config/`` resolved from this file's location is authoritative — never
    the process working directory. Files are read fresh on every call; there
    is no in-memory cache, so edits to root ``config/`` take effect on the
    next load after passing full validation.
    """

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

    def load_bundle(
        self, locale: str
    ) -> tuple[StageCatalog, RubricCatalog, ProgressionPolicy]:
        """Load catalog + rubrics + policy and cross-validate rubric references.

        Every stage's ``rubric_id`` must reference an existing rubric whose
        ``stage_id`` matches the stage. Raises :class:`ConfigLoadError` with a
        clear diagnostic otherwise; never falls back to hardcoded rules.
        """
        catalog = self.load_catalog(locale)
        rubrics = self.load_rubrics(locale)
        policy = self.load_policy(locale)
        by_id = {r.id: r for r in rubrics.rubrics}
        for stage in catalog.stages:
            rubric = by_id.get(stage.rubric_id)
            if rubric is None:
                raise ConfigLoadError(
                    f"stage {stage.id!r} references unknown "
                    f"rubric_id {stage.rubric_id!r}"
                )
            if rubric.stage_id != stage.id:
                raise ConfigLoadError(
                    f"rubric {rubric.id!r} stage_id {rubric.stage_id!r} "
                    f"does not match stage {stage.id!r}"
                )
        return catalog, rubrics, policy

    # -- cross-locale validation ------------------------------------------

    def validate_cross_locale_consistency(self) -> list[str]:
        """Return diagnostic messages if en-US and es-CO configs diverge.

        Compares everything locale must not change: stage IDs, order, numbers,
        prerequisites, rubric references, rubric IDs, criterion IDs, critical
        and required flags, dimension weights, score scales, and the full
        progression policy (dimensions, every gate, thresholds). Only
        student-facing presentation text may differ.
        """
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

        # Stage IDs and order
        ids_en = [s.id for s in cat_en.stages]
        ids_es = [s.id for s in cat_es.stages]
        if set(ids_en) != set(ids_es):
            diagnostics.append(
                f"stage IDs differ: en-only={set(ids_en) - set(ids_es)}, "
                f"es-only={set(ids_es) - set(ids_en)}"
            )
        if ids_en != ids_es:
            diagnostics.append("stage order differs between locales")

        by_en = {s.id: s for s in cat_en.stages}
        by_es = {s.id: s for s in cat_es.stages}
        for sid in set(ids_en) & set(ids_es):
            a, b = by_en[sid], by_es[sid]
            if a.number != b.number:
                diagnostics.append(
                    f"stage {sid!r} number differs: en={a.number} es={b.number}"
                )
            if a.prerequisites != b.prerequisites:
                diagnostics.append(
                    f"stage {sid!r} prerequisites differ: "
                    f"en={a.prerequisites} es={b.prerequisites}"
                )
            if a.rubric_id != b.rubric_id:
                diagnostics.append(
                    f"stage {sid!r} rubric_id differs: "
                    f"en={a.rubric_id!r} es={b.rubric_id!r}"
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

        def _crit_flags(rubric: StageRubric) -> set[tuple[str, bool, bool]]:
            return {
                (c.id, c.critical, c.required_for_decision)
                for d in rubric.dimensions
                for c in d.criteria
            }

        for rid in rub_ids_en & rub_ids_es:
            crit_en = _crit_flags(rub_map_en[rid])
            crit_es = _crit_flags(rub_map_es[rid])
            if crit_en != crit_es:
                diagnostics.append(
                    f"rubric {rid!r} criteria differ (id/critical/required): "
                    f"en-only={crit_en - crit_es}, es-only={crit_es - crit_en}"
                )
            # Weights
            weights_en = {d.id: d.weight for d in rub_map_en[rid].dimensions}
            weights_es = {d.id: d.weight for d in rub_map_es[rid].dimensions}
            if weights_en != weights_es:
                diagnostics.append(
                    f"rubric {rid!r} dimension weights differ: en={weights_en} es={weights_es}"
                )

        # Policy: full semantics must match, not just headline thresholds.
        # The shipped en/es policies are structurally identical files; the
        # loader still selects the per-locale file so presentation strings
        # follow the locale while scoring stays identical.
        gates_en = pol_en.decision_gates
        gates_es = pol_es.decision_gates
        for attr in (
            "minimum_overall_score",
            "minimum_each_dimension_score",
            "minimum_critical_criterion_score",
            "require_all_rubric_criteria_assessed",
            "require_evidence_for_each_dimension",
            "require_exit_challenge",
            "require_comprehension_check",
            "require_reproducible_artifact_or_observation",
            "all_gates_must_pass",
        ):
            if getattr(gates_en, attr) != getattr(gates_es, attr):
                diagnostics.append(
                    f"decision_gates.{attr} differs: "
                    f"en={getattr(gates_en, attr)} es={getattr(gates_es, attr)}"
                )
        if pol_en.required_dimensions != pol_es.required_dimensions:
            diagnostics.append(
                f"required_dimensions differ: en={pol_en.required_dimensions} "
                f"es={pol_es.required_dimensions}"
            )
        for key in ("min", "max"):
            if pol_en.score_scale.get(key) != pol_es.score_scale.get(key):
                diagnostics.append(
                    f"policy score_scale.{key} differs: "
                    f"en={pol_en.score_scale.get(key)} "
                    f"es={pol_es.score_scale.get(key)}"
                )
        for key in ("min", "max"):
            if rub_en.score_scale.get(key) != rub_es.score_scale.get(key):
                diagnostics.append(
                    f"rubric score_scale.{key} differs: "
                    f"en={rub_en.score_scale.get(key)} "
                    f"es={rub_es.score_scale.get(key)}"
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
