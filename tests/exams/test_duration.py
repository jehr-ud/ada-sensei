"""RQ-EXM-007: duration and overtime derive from persisted timestamps."""

from __future__ import annotations

from datetime import timedelta

from ada_sensei.exams.lifecycle import ExamLifecycle
from ada_sensei.exams.models import ExamEventType
from ada_sensei.exams.process import compute_duration_seconds, compute_overtime
from ada_sensei.exams.store import ExamStore
from ada_sensei.models import Timestamps
from exams_helpers import make_attempt, make_bus


def test_duration_and_overtime(tmp_path):
    store = ExamStore(tmp_path / "data")
    lifecycle = ExamLifecycle(store, make_bus())
    started = Timestamps.now() - timedelta(seconds=3700)
    attempt = make_attempt(started_at=started, allowed_duration_seconds=3600)
    store.save(attempt)

    lifecycle.request_finish(attempt, confirmed=True)
    lifecycle.finish(attempt, finished_at=started + timedelta(seconds=3700))

    assert attempt.duration_seconds == 3700
    assert attempt.overtime_seconds == 100
    assert compute_overtime(3700, 3600) == 100
    assert compute_duration_seconds(None, None) is None
    events = store.list_events(attempt.exam_attempt_id)
    assert any(e.type is ExamEventType.exam_finished for e in events)


def test_duration_within_limit_has_no_overtime(tmp_path):
    store = ExamStore(tmp_path / "data")
    lifecycle = ExamLifecycle(store, make_bus())
    started = Timestamps.now()
    attempt = make_attempt(started_at=started)
    store.save(attempt)
    lifecycle.request_finish(attempt, confirmed=True)
    lifecycle.finish(attempt, finished_at=started + timedelta(seconds=600))
    assert attempt.overtime_seconds == 0