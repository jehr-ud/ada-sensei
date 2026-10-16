"""Dynamic first-run onboarding from the validated catalog (spec 008, RQ-LRN-004/005).

The stage list, goal, and order derive from configuration; choosing a stage
never marks skipped prerequisites as mastered; locale changes preserve
records; exam stores stay untouched.
"""

from __future__ import annotations

import pytest
from ada_sensei.learning.catalog import LearningCatalogLoader
from ada_sensei.learning.onboarding import (
    OnboardingError,
    choose_starting_stage,
    get_onboarding_content,
    interpret_choice,
    render_onboarding,
    start_with_default,
    start_with_diagnostic,
)
from ada_sensei.learning.stores import LearningProfileStore


def _catalog(locale="en-US"):
    return LearningCatalogLoader().load_catalog(locale)


def test_onboarding_lists_all_configured_stages_in_order():
    content = get_onboarding_content(_catalog("en-US"), "en-US")
    loader_count = len(_catalog("en-US").stages)
    assert len(content.stages) == loader_count == 9
    assert [s.number for s in content.stages] == sorted(s.number for s in content.stages)
    assert content.catalog_version == "1.2.0"


def test_onboarding_uses_selected_locale_labels():
    en = get_onboarding_content(_catalog("en-US"), "en-US")
    es = get_onboarding_content(_catalog("es-CO"), "es-CO")
    assert [s.id for s in en.stages] == [s.id for s in es.stages]
    assert en.stages[0].title != es.stages[0].title
    text_es = render_onboarding(es)
    assert "Etapas de aprendizaje:" in text_es
    assert "1. Fundamentos de Kotlin" in text_es


def test_render_includes_goal_and_choices():
    text = render_onboarding(get_onboarding_content(_catalog("en-US"), "en-US"))
    assert "not merely copy generated code" in text
    assert "diagnose" in text and "skip" in text


def test_interpret_choice_keywords():
    assert interpret_choice("diagnose")[0] == "diagnose"
    assert interpret_choice("DIAGNÓSTICO")[0] == "diagnose"
    assert interpret_choice("skip")[0] == "skip"
    assert interpret_choice("omitir")[0] == "skip"
    assert interpret_choice("") == ("skip", "")
    assert interpret_choice("6") == ("stage", "6")
    assert interpret_choice("Kotlin-Fundamentals") == ("stage", "Kotlin-Fundamentals")


def test_choose_stage_by_number_and_id(tmp_path):
    store = LearningProfileStore(str(tmp_path))
    profile, unmet = choose_starting_stage(
        store, _catalog(), student_id="Ada", locale="en-US", selection="6"
    )
    assert profile.current_stage_id == "android-basic-application"
    assert profile.catalog_version == "1.2.0"
    assert profile.selected_locale == "en-US"
    assert profile.diagnostic_completed is False
    profile2, _ = choose_starting_stage(
        store, _catalog(), student_id="Bob", locale="es-CO", selection="KOTLIN-FUNDAMENTALS"
    )
    assert profile2.current_stage_id == "kotlin-fundamentals"


def test_unknown_stage_selection_errors_clearly(tmp_path):
    store = LearningProfileStore(str(tmp_path))
    with pytest.raises(OnboardingError, match="valid stages"):
        choose_starting_stage(
            store, _catalog(), student_id="Ada", locale="en-US", selection="cobol"
        )
    assert store.get("Ada") is None  # failed choice persists nothing


def test_unmet_prerequisites_disclosed_not_mastered(tmp_path):
    store = LearningProfileStore(str(tmp_path))
    profile, unmet = choose_starting_stage(
        store, _catalog(), student_id="Ada", locale="en-US", selection="3"
    )
    assert profile.current_stage_id == "activities-lifecycle"
    assert unmet == ["android-project-structure"]
    assert profile.mastered_stages == []


def test_diagnostic_and_default_paths(tmp_path):
    store = LearningProfileStore(str(tmp_path))
    profile = start_with_diagnostic(
        store, _catalog(), student_id="Ada", locale="en-US"
    )
    assert profile.current_stage_id == "kotlin-fundamentals"
    assert profile.diagnostic_completed is True
    profile2 = start_with_default(
        store, _catalog(), student_id="Bob", locale="es-CO"
    )
    assert profile2.diagnostic_completed is False
    assert profile2.selected_locale == "es-CO"


def test_locale_change_preserves_learning_records(tmp_path):
    from ada_sensei.locale.service import LocaleService
    from ada_sensei.locale.store import LocalePreferenceStore

    store = LearningProfileStore(str(tmp_path))
    choose_starting_stage(
        store, _catalog(), student_id="Ada", locale="es-CO", selection="5"
    )
    LocaleService(LocalePreferenceStore(str(tmp_path))).set_locale("Ada", "en-US")
    profile = store.get("Ada")
    assert profile.current_stage_id == "state-basic-architecture"
    assert profile.mastered_stages == []
