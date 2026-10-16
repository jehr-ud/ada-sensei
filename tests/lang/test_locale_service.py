"""Tests for LocaleService and LocalePreferenceStore (spec 0010)."""
from __future__ import annotations

from pathlib import Path

import pytest
from ada_sensei.locale.models import SUPPORTED_LOCALES
from ada_sensei.locale.service import LocaleService
from ada_sensei.locale.store import LocalePreferenceStore


def _make_service(tmp_path: Path) -> LocaleService:
    store = LocalePreferenceStore(tmp_path)
    return LocaleService(store)


def test_first_run_returns_none(tmp_path):
    svc = _make_service(tmp_path)
    result = svc.get_or_prompt_locale("student://alice")
    assert result is None


def test_set_and_get_locale(tmp_path):
    svc = _make_service(tmp_path)
    pref = svc.set_locale("student://alice", "es-CO")
    assert pref.locale == "es-CO"
    assert pref.locale_source == "student_selection"

    saved = svc.get_or_prompt_locale("student://alice")
    assert saved == "es-CO"


def test_change_locale_persists(tmp_path):
    svc = _make_service(tmp_path)
    svc.set_locale("student://alice", "es-CO")
    svc.set_locale("student://alice", "en-US")
    saved = svc.get_or_prompt_locale("student://alice")
    assert saved == "en-US"


def test_invalid_locale_raises(tmp_path):
    svc = _make_service(tmp_path)
    with pytest.raises(ValueError, match="unsupported locale"):
        svc.set_locale("student://alice", "fr-FR")


def test_validate_locale_rejects_unsupported():
    with pytest.raises(ValueError):
        LocaleService.validate_locale("de-DE")


def test_validate_locale_accepts_supported():
    for loc in SUPPORTED_LOCALES:
        assert LocaleService.validate_locale(loc) == loc


def test_change_locale_does_not_modify_other_student(tmp_path):
    svc = _make_service(tmp_path)
    svc.set_locale("student://alice", "es-CO")
    svc.set_locale("student://bob", "en-US")

    assert svc.get_or_prompt_locale("student://alice") == "es-CO"
    assert svc.get_or_prompt_locale("student://bob") == "en-US"


def test_resolve_bundle_returns_three_objects(tmp_path):
    from ada_sensei.learning.catalog import LearningCatalogLoader
    store = LocalePreferenceStore(tmp_path)
    loader = LearningCatalogLoader()
    svc = LocaleService(store, loader)
    catalog, rubrics, policy = svc.resolve_bundle("en-US")
    assert len(catalog.stages) > 0
    assert len(rubrics.rubrics) > 0
    assert policy.policy_id


def test_cross_locale_stage_ids_identical():
    """Stage IDs must be identical across locales — spec 0010 RQ-LNG-007."""
    from ada_sensei.learning.catalog import LearningCatalogLoader
    loader = LearningCatalogLoader()
    cat_en = loader.load_catalog("en-US")
    cat_es = loader.load_catalog("es-CO")
    assert {s.id for s in cat_en.stages} == {s.id for s in cat_es.stages}


def test_cross_locale_weights_identical():
    """Rubric weights must be identical across locales — spec 0010 RQ-LNG-010."""
    from ada_sensei.learning.catalog import LearningCatalogLoader
    loader = LearningCatalogLoader()
    en = loader.load_rubrics("en-US")
    es = loader.load_rubrics("es-CO")
    en_map = {r.id: r for r in en.rubrics}
    es_map = {r.id: r for r in es.rubrics}
    for rid in en_map:
        if rid in es_map:
            for d_en, d_es in zip(en_map[rid].dimensions, es_map[rid].dimensions):
                assert d_en.weight == d_es.weight, f"{rid} dimension {d_en.id} weight differs"


def test_cross_locale_gate_thresholds_identical():
    """Gate thresholds must be identical across locales — spec 0010 RQ-LNG-010."""
    from ada_sensei.learning.catalog import LearningCatalogLoader
    loader = LearningCatalogLoader()
    pol_en = loader.load_policy("en-US")
    pol_es = loader.load_policy("es-CO")
    assert pol_en.decision_gates.minimum_overall_score == pol_es.decision_gates.minimum_overall_score
    assert pol_en.decision_gates.minimum_critical_criterion_score == pol_es.decision_gates.minimum_critical_criterion_score
