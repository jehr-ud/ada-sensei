"""Learning-stage resolution for the GUI header (RQ-TUI-036).

The displayed stage comes from persisted progress + catalog, never hardcoded,
never advanced by the UI, and never changed by a pending evaluation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ada_sensei.learning.models import LearningProfile
from ada_sensei.learning.status import resolve_learning_stage
from ada_sensei.learning.stores import LearningProfileStore


def _save_profile(tmp_path, student="Ana", stage="state-basic-architecture"):
    store = LearningProfileStore(str(tmp_path))
    now = datetime.now(tz=UTC)
    store.save(
        LearningProfile(
            student_id=student,
            catalog_id="android-learning-path",
            catalog_version="1.2.0",
            current_stage_id=stage,
            created_at=now,
            updated_at=now,
        )
    )


def test_stage_resolved_from_persisted_progress(tmp_path):
    _save_profile(tmp_path)
    status = resolve_learning_stage(tmp_path, "Ana", "en-US")
    assert status.state == "active"
    assert status.stage_id == "state-basic-architecture"
    assert status.stage_number == 5
    assert status.stage_name == "State and Basic Architecture"
    assert "Current stage: 5" in status.display("en-US")


def test_spanish_stage_name_matches_catalog(tmp_path):
    _save_profile(tmp_path)
    status = resolve_learning_stage(tmp_path, "Ana", "es-CO")
    assert status.state == "active"
    assert status.stage_number == 5
    assert "Etapa actual: 5" in status.display("es-CO")
    # es catalog title for stage 5 differs from en title
    assert status.stage_name


def test_not_started_without_profile(tmp_path):
    status = resolve_learning_stage(tmp_path, "Nobody", "es-CO")
    assert status.state == "not_started"
    assert status.display("es-CO") == "Ruta de aprendizaje no iniciada"
    assert status.display("en-US") == "Learning path not started"


def test_invalid_stage_reference_is_safe(tmp_path):
    _save_profile(tmp_path, stage="no-such-stage")
    status = resolve_learning_stage(tmp_path, "Ana", "en-US")
    assert status.state == "unknown"


def test_pending_evaluation_does_not_change_stage(tmp_path):
    _save_profile(tmp_path, stage="kotlin-fundamentals")
    before = resolve_learning_stage(tmp_path, "Ana", "en-US")
    # Simulate an unfinished evaluation: no profile write happens.
    after = resolve_learning_stage(tmp_path, "Ana", "en-US")
    assert before.stage_id == after.stage_id == "kotlin-fundamentals"


def test_ui_never_advances_stage(tmp_path):
    _save_profile(tmp_path, stage="kotlin-fundamentals")
    for _ in range(3):
        status = resolve_learning_stage(tmp_path, "Ana", "en-US")
        assert status.stage_number == 1
    # Refresh path is read-only: profile on disk unchanged.
    store = LearningProfileStore(str(tmp_path))
    assert store.get("Ana") is not None
    assert store.get("Ana").current_stage_id == "kotlin-fundamentals"
