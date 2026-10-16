"""Config validation, resolution, parity, and behavior tests (spec 008, RQ-LRN-016/024).

 Covers: schema versions, duplicate IDs/numbers, default-stage and rubric
 references, prerequisite cycles, weight/threshold validation, missing and
 malformed config, CWD-independent root resolution, full locale parity with
 divergence detection, config-change-driven behavior, no hardcoded fallback,
 version persistence, and exam/mastery store separation.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from ada_sensei.learning.catalog import ConfigLoadError, LearningCatalogLoader
from ada_sensei.learning.models import (
    CriterionResult,
    DimensionResult,
    MasteryAssessment,
)

ROOT_CONFIG = Path(__file__).resolve().parents[2] / "config"


def _copy_en_config(tmp_path: Path) -> Path:
    for name in (
        "stages.en.json",
        "stage-rubrics.en.json",
        "progression-policy.en.json",
        "stages.es.json",
        "stage-rubrics.es.json",
        "progression-policy.es.json",
    ):
        shutil.copy(ROOT_CONFIG / name, tmp_path / name)
    return tmp_path


def _write(tmp_path: Path, name: str, data: dict) -> None:
    (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")


# -- resolution ---------------------------------------------------------------


def test_default_loader_resolves_repo_root_config_from_any_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # must not depend on the working directory
    loader = LearningCatalogLoader()
    catalog = loader.load_catalog("en-US")
    assert len(catalog.stages) == 9
    assert catalog.catalog_id == "android-learning-path"


def test_explicit_config_dir_takes_precedence(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["title"] = "Override catalog"
    _write(tmp_path, "stages.en.json", data)
    catalog = LearningCatalogLoader(config_dir=tmp_path).load_catalog("en-US")
    assert catalog.title == "Override catalog"


def test_no_silent_hardcoded_fallback_on_missing_dir(tmp_path):
    loader = LearningCatalogLoader(config_dir=tmp_path / "absent")
    with pytest.raises(ConfigLoadError, match="not found"):
        loader.load_catalog("en-US")


def test_malformed_json_reported(tmp_path):
    _copy_en_config(tmp_path)
    (tmp_path / "progression-policy.en.json").write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="invalid JSON"):
        LearningCatalogLoader(config_dir=tmp_path).load_policy("en-US")


def test_unsupported_schema_version_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["schema_version"] = "9.9.9"
    _write(tmp_path, "stages.en.json", data)
    with pytest.raises(ConfigLoadError, match="schema_version"):
        LearningCatalogLoader(config_dir=tmp_path).load_catalog("en-US")


def test_unsupported_rubric_schema_version_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads(
        (tmp_path / "stage-rubrics.en.json").read_text(encoding="utf-8")
    )
    data["schema_version"] = "0.0.1"
    _write(tmp_path, "stage-rubrics.en.json", data)
    with pytest.raises(ConfigLoadError, match="schema_version"):
        LearningCatalogLoader(config_dir=tmp_path).load_rubrics("en-US")


# -- catalog validation --------------------------------------------------------


def test_duplicate_stage_numbers_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["stages"][1]["number"] = data["stages"][0]["number"]
    _write(tmp_path, "stages.en.json", data)
    with pytest.raises(ConfigLoadError, match="duplicate stage numbers"):
        LearningCatalogLoader(config_dir=tmp_path).load_catalog("en-US")


def test_unknown_default_stage_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["default_stage_id"] = "no-such-stage"
    _write(tmp_path, "stages.en.json", data)
    with pytest.raises(ConfigLoadError, match="default_stage_id"):
        LearningCatalogLoader(config_dir=tmp_path).load_catalog("en-US")


def test_unknown_prerequisite_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["stages"][0]["prerequisites"] = ["ghost-stage"]
    _write(tmp_path, "stages.en.json", data)
    with pytest.raises(ConfigLoadError, match="unknown prerequisite"):
        LearningCatalogLoader(config_dir=tmp_path).load_catalog("en-US")


def test_prerequisite_cycle_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["stages"][0]["prerequisites"] = [data["stages"][1]["id"]]
    data["stages"][1]["prerequisites"] = [data["stages"][0]["id"]]
    _write(tmp_path, "stages.en.json", data)
    with pytest.raises(ConfigLoadError, match="cycle"):
        LearningCatalogLoader(config_dir=tmp_path).load_catalog("en-US")


def test_stage_rubric_reference_validated_in_bundle(tmp_path):
    _copy_en_config(tmp_path)
    loader = LearningCatalogLoader(config_dir=tmp_path)
    catalog, rubrics, _ = loader.load_bundle("en-US")
    assert len(catalog.stages) == len(rubrics.rubrics)
    data = json.loads((tmp_path / "stages.en.json").read_text(encoding="utf-8"))
    data["stages"][0]["rubric_id"] = "rubric-that-does-not-exist"
    _write(tmp_path, "stages.en.json", data)
    with pytest.raises(ConfigLoadError, match="rubric_id"):
        LearningCatalogLoader(config_dir=tmp_path).load_bundle("en-US")


def test_duplicate_criterion_ids_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads(
        (tmp_path / "stage-rubrics.en.json").read_text(encoding="utf-8")
    )
    crit = data["rubrics"][0]["dimensions"][0]["criteria"][0]
    data["rubrics"][0]["dimensions"][1]["criteria"].append(crit)
    _write(tmp_path, "stage-rubrics.en.json", data)
    with pytest.raises(ConfigLoadError, match="duplicate criterion id"):
        LearningCatalogLoader(config_dir=tmp_path).load_rubrics("en-US")


def test_invalid_dimension_weights_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads(
        (tmp_path / "stage-rubrics.en.json").read_text(encoding="utf-8")
    )
    data["rubrics"][0]["dimensions"][0]["weight"] = 0.9
    _write(tmp_path, "stage-rubrics.en.json", data)
    with pytest.raises(ConfigLoadError, match="weights sum"):
        LearningCatalogLoader(config_dir=tmp_path).load_rubrics("en-US")


def test_invalid_policy_dimension_weights_rejected(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads(
        (tmp_path / "progression-policy.en.json").read_text(encoding="utf-8")
    )
    data["required_dimensions"]["construction"] = 0.1
    _write(tmp_path, "progression-policy.en.json", data)
    with pytest.raises(ConfigLoadError, match="sum to"):
        LearningCatalogLoader(config_dir=tmp_path).load_policy("en-US")


# -- parity --------------------------------------------------------------------


def test_shipped_locales_fully_consistent():
    diagnostics = LearningCatalogLoader().validate_cross_locale_consistency()
    assert diagnostics == ["cross-locale consistency: OK"]


def test_parity_detects_critical_flag_divergence(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads(
        (tmp_path / "stage-rubrics.es.json").read_text(encoding="utf-8")
    )
    for rubric in data["rubrics"]:
        for dim in rubric["dimensions"]:
            for crit in dim["criteria"]:
                if crit.get("critical"):
                    crit["critical"] = False
                    break
            break
        break
    _write(tmp_path, "stage-rubrics.es.json", data)
    diagnostics = LearningCatalogLoader(
        config_dir=tmp_path
    ).validate_cross_locale_consistency()
    assert any("critical" in d or "criteria differ" in d for d in diagnostics)


def test_parity_detects_gate_divergence(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads(
        (tmp_path / "progression-policy.es.json").read_text(encoding="utf-8")
    )
    data["decision_gates"]["minimum_overall_score"] = 1.0
    _write(tmp_path, "progression-policy.es.json", data)
    diagnostics = LearningCatalogLoader(
        config_dir=tmp_path
    ).validate_cross_locale_consistency()
    assert any("minimum_overall_score" in d for d in diagnostics)


def test_parity_detects_prerequisite_divergence(tmp_path):
    _copy_en_config(tmp_path)
    data = json.loads((tmp_path / "stages.es.json").read_text(encoding="utf-8"))
    data["stages"][2]["prerequisites"] = []
    _write(tmp_path, "stages.es.json", data)
    diagnostics = LearningCatalogLoader(
        config_dir=tmp_path
    ).validate_cross_locale_consistency()
    assert any("prerequisites differ" in d for d in diagnostics)


# -- config-driven behavior ------------------------------------------------------


def _full_score_assessment():
    from datetime import UTC, datetime

    from ada_sensei.urns import URN

    loader = LearningCatalogLoader()
    rubrics = loader.load_rubrics("en-US")
    rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
    refs = ["source_code://x.kt"]
    dim_results = [
        DimensionResult(
            dimension_id=d.id,
            score=3.5,
            criterion_results=[
                CriterionResult(criterion_id=c.id, score=3.5, evidence_refs=refs)
                for c in d.criteria
            ],
            evidence_refs=refs,
        )
        for d in rubric.dimensions
    ]
    return MasteryAssessment(
        id=URN.make("learning"),
        student_id="student://t",
        project_id="project://t",
        stage_id="kotlin-fundamentals",
        rubric_id=rubric.id,
        rubric_version=rubric.version,
        policy_id="mastery-progression-default-v1",
        policy_version="1.0.0",
        catalog_version="1.2.0",
        dimension_results=dim_results,
        overall_score=3.5,
        evidence_refs=refs,
        exit_challenge_completed=True,
        comprehension_check_completed=True,
        created_at=datetime.now(tz=UTC),
    )


def test_config_threshold_change_flips_decision_without_code_change(tmp_path):
    from ada_sensei.learning.progression import ProgressionPolicyEngine

    _copy_en_config(tmp_path)
    strict = LearningCatalogLoader(config_dir=tmp_path)
    policy = strict.load_policy("en-US")
    rubrics = strict.load_rubrics("en-US")
    rubric = strict.get_rubric_for_stage("kotlin-fundamentals", rubrics)
    engine = ProgressionPolicyEngine()
    assessment = _full_score_assessment()
    assert (
        engine.evaluate(assessment, rubric, policy, next_stage_id="s2").status
        == "READY"
    )

    data = json.loads(
        (tmp_path / "progression-policy.en.json").read_text(encoding="utf-8")
    )
    data["decision_gates"]["minimum_overall_score"] = 3.9
    _write(tmp_path, "progression-policy.en.json", data)
    strict_policy = LearningCatalogLoader(config_dir=tmp_path).load_policy("en-US")
    decision = engine.evaluate(assessment, rubric, strict_policy, next_stage_id="s2")
    assert decision.status == "NOT_READY"


def test_locale_change_does_not_alter_decision():
    from ada_sensei.learning.progression import ProgressionPolicyEngine

    loader = LearningCatalogLoader()
    engine = ProgressionPolicyEngine()
    assessment = _full_score_assessment()
    results = []
    for locale in ("en-US", "es-CO"):
        policy = loader.load_policy(locale)
        rubrics = loader.load_rubrics(locale)
        rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
        decision = engine.evaluate(assessment, rubric, policy, next_stage_id="s2")
        results.append((decision.status, decision.overall_score if hasattr(decision, "overall_score") else None, [g.passed for g in decision.gate_results]))
    assert results[0][0] == results[1][0] == "READY"
    assert results[0][2] == results[1][2]


def test_decision_propagates_assessment_versions():
    from ada_sensei.learning.progression import ProgressionPolicyEngine

    loader = LearningCatalogLoader()
    policy = loader.load_policy("en-US")
    rubrics = loader.load_rubrics("en-US")
    rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
    assessment = _full_score_assessment()
    assessment.catalog_version = "9.9.9-custom"
    decision = ProgressionPolicyEngine().evaluate(
        assessment, rubric, policy, next_stage_id="s2"
    )
    assert decision.policy_id == assessment.policy_id
    assert decision.policy_version == assessment.policy_version
    assert decision.assessment_id == assessment.id


# -- exam / mastery separation ----------------------------------------------------


def test_exam_and_mastery_stores_are_independent(tmp_path):
    from ada_sensei.exams.store import ExamStore
    from ada_sensei.learning.stores import LearningProfileStore

    from conftest import seed_learning_profile

    seed_learning_profile(tmp_path, "Ada", stage_id="kotlin-fundamentals")
    exam_store = ExamStore(str(tmp_path))
    assert exam_store.get("learning://profile-Ada") is None
    profile_store = LearningProfileStore(str(tmp_path))
    assert profile_store.get("Ada") is not None
    assert profile_store.get("Ada").current_stage_id == "kotlin-fundamentals"


def test_progression_engine_never_writes_student_state(tmp_path):
    from ada_sensei.learning.progression import ProgressionPolicyEngine
    from ada_sensei.learning.stores import LearningProfileStore

    from conftest import seed_learning_profile

    seed_learning_profile(tmp_path, "Ada", stage_id="kotlin-fundamentals")
    loader = LearningCatalogLoader()
    policy = loader.load_policy("en-US")
    rubrics = loader.load_rubrics("en-US")
    rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
    ProgressionPolicyEngine().evaluate(
        _full_score_assessment(), rubric, policy, next_stage_id="s2"
    )
    assert (
        LearningProfileStore(str(tmp_path)).get("Ada").current_stage_id
        == "kotlin-fundamentals"
    )
