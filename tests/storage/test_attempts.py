from __future__ import annotations

from ada_sensei.models import AssistanceLevel, Attempt, AttemptStatus
from ada_sensei.storage.attempts import AttemptStore


def test_roundtrip_and_status(tmp_path):
    store = AttemptStore(str(tmp_path))
    attempt = Attempt(
        student_id="student://a", project_id="project://p", exercise_id="exercise://e"
    )
    store.save(attempt)
    loaded = store.get(attempt.id)
    assert loaded is not None
    assert loaded.student_id == "student://a"
    assert loaded.status == AttemptStatus.in_progress

    marked = store.mark_completed(attempt.id)
    assert marked.status == AttemptStatus.completed
    assert store.get(attempt.id).status == AttemptStatus.completed


def test_mark_completed_after_eval(tmp_path):
    store = AttemptStore(str(tmp_path))
    attempt = Attempt()
    store.save(attempt)
    result = store.mark_completed(attempt.id)
    assert result.status == AttemptStatus.completed


def test_update_assistance_and_hints(tmp_path):
    store = AttemptStore(str(tmp_path))
    attempt = Attempt()
    store.save(attempt)
    store.add_hint(attempt.id, "hint one")
    store.update_assistance(attempt.id, AssistanceLevel.hint)
    loaded = store.get(attempt.id)
    assert loaded.hints_used == ["hint one"]
    assert loaded.assistance_level == AssistanceLevel.hint
