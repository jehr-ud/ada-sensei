"""RQ-EXM-003/004: start creates the attempt and docs; completion is immutable."""

from __future__ import annotations

import pytest
from ada_sensei.exams.docs import (
    CONTEXT_NAME,
    README_NAME,
    RUBRIC_NAME,
    ExamDocs,
    is_generated,
)
from ada_sensei.exams.models import ExamEventType, ExamStatus
from ada_sensei.exams.store import ExamStore
from exams_helpers import make_bus, make_definition, make_lifecycle, make_project


def test_start_creates_attempt_and_docs(tmp_path):
    project = make_project(tmp_path)
    store = ExamStore(tmp_path / "data")
    bus = make_bus()
    lifecycle = make_lifecycle(store, bus, project)
    definition = make_definition()

    attempt = lifecycle.start(
        definition,
        student_id="student://s1",
        project_id="project://p1",
        project_root=project,
    )

    assert attempt.status is ExamStatus.active
    assert attempt.exam_id == definition.exam_id
    assert attempt.allowed_ask_count == 4
    assert lifecycle.bridge_attached

    saved = store.get(attempt.exam_attempt_id)
    assert saved is not None and saved.is_active

    started = store.list_events(attempt.exam_attempt_id)
    assert any(e.type is ExamEventType.exam_started for e in started)

    assert store.get_definition(definition.exam_id) is not None
    docs = ExamDocs(project, definition.exam_id)
    for name in (README_NAME, CONTEXT_NAME, RUBRIC_NAME):
        assert docs.path(name).exists()
        assert is_generated(docs.path(name))


def test_completed_attempt_is_immutable(tmp_path):
    project = make_project(tmp_path)
    store = ExamStore(tmp_path / "data")
    bus = make_bus()
    lifecycle = make_lifecycle(store, bus, project)
    attempt = lifecycle.start(
        make_definition(),
        student_id="student://s1",
        project_id="project://p1",
        project_root=project,
    )

    lifecycle.request_finish(attempt, confirmed=True)
    lifecycle.finish(attempt)
    from ada_sensei.exams.models import ExamAttemptImmutableError

    completed = store.get(attempt.exam_attempt_id)
    assert completed is not None and completed.is_completed
    with pytest.raises(ExamAttemptImmutableError):
        store.save(completed.model_copy(update={"ask_count": 99}))
    with pytest.raises(ExamAttemptImmutableError):
        store.save(completed.model_copy(update={"status": ExamStatus.active}))

    administrative = store.save(
        completed.model_copy(update={"administrative_metadata": {"note": "ok"}})
    )
    assert administrative.administrative_metadata == {"note": "ok"}