"""Tests for LearningCatalogLoader (spec 008-learning-path)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from ada_sensei.learning.catalog import ConfigLoadError, LearningCatalogLoader
from ada_sensei.learning.models import ProgressionPolicy, RubricCatalog, StageCatalog


def test_load_catalog_en():
    loader = LearningCatalogLoader()
    catalog = loader.load_catalog("en-US")
    assert isinstance(catalog, StageCatalog)
    assert len(catalog.stages) > 0
    assert catalog.locale == "en-US"


def test_load_catalog_es():
    loader = LearningCatalogLoader()
    catalog = loader.load_catalog("es-CO")
    assert isinstance(catalog, StageCatalog)
    assert len(catalog.stages) > 0
    assert catalog.locale == "es-CO"


def test_stage_ids_stable_across_locales():
    loader = LearningCatalogLoader()
    en = loader.load_catalog("en-US")
    es = loader.load_catalog("es-CO")
    ids_en = {s.id for s in en.stages}
    ids_es = {s.id for s in es.stages}
    assert ids_en == ids_es, f"Stage IDs differ: en-only={ids_en - ids_es}, es-only={ids_es - ids_en}"


def test_load_rubrics_en():
    loader = LearningCatalogLoader()
    rubrics = loader.load_rubrics("en-US")
    assert isinstance(rubrics, RubricCatalog)
    assert len(rubrics.rubrics) > 0


def test_rubric_ids_stable_across_locales():
    loader = LearningCatalogLoader()
    en = loader.load_rubrics("en-US")
    es = loader.load_rubrics("es-CO")
    ids_en = {r.id for r in en.rubrics}
    ids_es = {r.id for r in es.rubrics}
    assert ids_en == ids_es, "Rubric IDs differ"


def test_rubric_dimension_weights_sum_to_one():
    loader = LearningCatalogLoader()
    rubrics = loader.load_rubrics("en-US")
    for rubric in rubrics.rubrics:
        total = sum(d.weight for d in rubric.dimensions)
        assert abs(total - 1.0) < 0.001, f"Rubric {rubric.id} weights sum to {total}"


def test_load_policy_en():
    loader = LearningCatalogLoader()
    policy = loader.load_policy("en-US")
    assert isinstance(policy, ProgressionPolicy)
    assert policy.decision_gates.minimum_overall_score > 0


def test_policy_gates_identical_across_locales():
    loader = LearningCatalogLoader()
    en = loader.load_policy("en-US")
    es = loader.load_policy("es-CO")
    assert en.decision_gates.minimum_overall_score == es.decision_gates.minimum_overall_score
    assert en.decision_gates.minimum_each_dimension_score == es.decision_gates.minimum_each_dimension_score
    assert en.decision_gates.minimum_critical_criterion_score == es.decision_gates.minimum_critical_criterion_score


def test_unsupported_locale_raises():
    loader = LearningCatalogLoader()
    with pytest.raises(ConfigLoadError, match="unsupported locale"):
        loader.load_catalog("fr-FR")


def test_get_rubric_for_stage():
    loader = LearningCatalogLoader()
    rubrics = loader.load_rubrics("en-US")
    # kotlin-fundamentals always present
    rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
    assert rubric.stage_id == "kotlin-fundamentals"


def test_missing_rubric_for_stage_raises():
    loader = LearningCatalogLoader()
    rubrics = loader.load_rubrics("en-US")
    with pytest.raises(ConfigLoadError, match="no rubric found"):
        loader.get_rubric_for_stage("nonexistent-stage", rubrics)


def test_validate_cross_locale_consistency():
    loader = LearningCatalogLoader()
    diagnostics = loader.validate_cross_locale_consistency()
    assert diagnostics, "should return at least one diagnostic"
    # Expect "OK" if files are consistent
    failures = [d for d in diagnostics if "differ" in d]
    assert not failures, f"Cross-locale inconsistencies found: {failures}"


def test_invalid_config_dir_raises(tmp_path: Path):
    loader = LearningCatalogLoader(config_dir=tmp_path)
    with pytest.raises(ConfigLoadError, match="not found"):
        loader.load_catalog("en-US")


def test_invalid_json_raises(tmp_path: Path):
    (tmp_path / "stages.en.json").write_text("not json", encoding="utf-8")
    loader = LearningCatalogLoader(config_dir=tmp_path)
    with pytest.raises(ConfigLoadError, match="invalid JSON"):
        loader.load_catalog("en-US")


def test_duplicate_stage_ids_raises(tmp_path: Path):
    loader = LearningCatalogLoader()
    catalog = loader.load_catalog("en-US")
    data = catalog.model_dump(mode="json")
    # Duplicate the first stage
    data["stages"].append(data["stages"][0])
    (tmp_path / "stages.en.json").write_text(json.dumps(data), encoding="utf-8")
    bad_loader = LearningCatalogLoader(config_dir=tmp_path)
    with pytest.raises(ConfigLoadError, match="duplicate"):
        bad_loader.load_catalog("en-US")
