"""Bilingual GUI strings (RQ-TUI-038, RQ-LNG-005/007/008)."""

from __future__ import annotations

from ada_sensei.locale.ui_strings import get_ui_string


def test_selector_and_status_localized():
    assert get_ui_string("selector_title", "es-CO") == "Acción"
    assert get_ui_string("selector_title", "en-US") == "Action"
    assert "Etapa actual" in get_ui_string("stage_current", "es-CO")
    assert "Current stage" in get_ui_string("stage_current", "en-US")
    assert get_ui_string("stage_not_started", "es-CO") == (
        "Ruta de aprendizaje no iniciada"
    )
    assert get_ui_string("stage_not_started", "en-US") == "Learning path not started"


def test_missing_translation_uses_fallback():
    assert get_ui_string("selector_title", "fr-FR") == "Action"
    assert get_ui_string("selector_title", None) == "Action"
    assert get_ui_string("no_such_key_xyz", "es-CO") == "no_such_key_xyz"


def test_version_value_is_language_independent():
    es = get_ui_string("version_label", "es-CO").format(version="0.1.0")
    en = get_ui_string("version_label", "en-US").format(version="0.1.0")
    assert "0.1.0" in es and "0.1.0" in en
    assert es != en  # chrome localized, value identical


def test_switching_locale_does_not_touch_progress(tmp_path):
    from datetime import UTC, datetime

    from ada_sensei.learning.models import LearningProfile
    from ada_sensei.learning.stores import LearningProfileStore
    from ada_sensei.locale.service import LocaleService
    from ada_sensei.locale.store import LocalePreferenceStore

    store = LearningProfileStore(str(tmp_path))
    now = datetime.now(tz=UTC)
    store.save(
        LearningProfile(
            student_id="Ana",
            catalog_id="android-learning-path",
            catalog_version="1.2.0",
            current_stage_id="kotlin-fundamentals",
            created_at=now,
            updated_at=now,
        )
    )
    svc = LocaleService(LocalePreferenceStore(str(tmp_path)))
    svc.set_locale("Ana", "es-CO")
    assert store.get("Ana").current_stage_id == "kotlin-fundamentals"
    svc.set_locale("Ana", "en-US")
    assert store.get("Ana").current_stage_id == "kotlin-fundamentals"
    assert svc.get_or_prompt_locale("Ana") == "en-US"
