"""RQ-EXM-005/006/031: ask count comes from the event log, never from text."""

from __future__ import annotations

import json

from ada_sensei.actions.ask import AskAction
from ada_sensei.actions.examine import ExamineAction
from ada_sensei.events import (
    ASK_CANCELLED,
    ASK_COMPLETED,
    ASK_FAILED,
    ASK_STARTED,
    AppEvent,
)
from ada_sensei.exams.models import ExamEventType
from ada_sensei.exams.store import ExamStore
from ada_sensei.llm.base import LLMClient
from exams_helpers import (
    make_attempt,
    make_bus,
    make_context,
    make_definition,
    make_lifecycle,
)


def _emit(bus, name, attempt_id, question_id=None):
    bus.emit(
        AppEvent(
            name,
            {
                "question_id": question_id,
                "duration_ms": 100,
                "exam_attempt_id": attempt_id,
            },
        )
    )


def test_ask_counted_from_app_events(tmp_path):
    store = ExamStore(tmp_path / "data")
    bus = make_bus()
    lifecycle = make_lifecycle(store, bus)
    attempt = lifecycle.start(
        make_definition(),
        student_id="student://s1",
        project_id="project://p1",
    )

    _emit(bus, ASK_STARTED, attempt.exam_attempt_id)
    _emit(bus, ASK_COMPLETED, attempt.exam_attempt_id, "q://1")
    _emit(bus, ASK_STARTED, attempt.exam_attempt_id)
    _emit(bus, ASK_COMPLETED, attempt.exam_attempt_id, "q://2")
    _emit(bus, ASK_STARTED, attempt.exam_attempt_id)
    _emit(bus, ASK_FAILED, attempt.exam_attempt_id)
    _emit(bus, ASK_CANCELLED, attempt.exam_attempt_id)

    assert attempt.ask_count == 2
    persisted = store.get(attempt.exam_attempt_id)
    assert persisted is not None and persisted.ask_count == 2


def test_ask_event_persisted(tmp_path):
    store = ExamStore(tmp_path / "data")
    bus = make_bus()
    lifecycle = make_lifecycle(store, bus)
    attempt = lifecycle.start(
        make_definition(),
        student_id="student://s1",
        project_id="project://p1",
    )
    _emit(bus, ASK_STARTED, attempt.exam_attempt_id)
    _emit(bus, ASK_COMPLETED, attempt.exam_attempt_id, "q://10")

    events = store.list_events(attempt.exam_attempt_id)
    completed = [e for e in events if e.type is ExamEventType.ask_completed]
    assert len(completed) == 1
    assert completed[0].question_id == "q://10"
    assert completed[0].counts_toward_allowance
    assert store.count_events(
        attempt.exam_attempt_id, ExamEventType.ask_completed
    ) == 1


def test_counts_ignore_llm_text(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    services = make_context(tmp_path, project)
    store = ExamStore(services.data_dir)
    attempt = make_attempt(exam_id="exam://test-exam")
    attempt.ask_count = 999  # a stale, text-influenced total
    store.save(attempt)
    from ada_sensei.exams.models import ASK_SUCCESS_EVENTS, ExamEvent

    for index in range(2):
        event = ExamEvent(
            exam_attempt_id=attempt.exam_attempt_id,
            type=ASK_SUCCESS_EVENTS[0],
            question_id=f"q://{index}",
        )
        store.append(event)

    services.context.exam_attempt_id = attempt.exam_attempt_id
    action = ExamineAction(services)

    recounted = action._require_active_attempt()
    assert recounted.ask_count == 2


def _ask_services(tmp_path):
    """Services with a fake tutor client, wired to the session event bus."""
    project = tmp_path / "proj"
    project.mkdir(parents=True, exist_ok=True)
    (project / "MainViewModel.kt").write_text(
        "class MainViewModel { val items = mutableStateListOf() }\n",
        encoding="utf-8",
    )
    return make_context(tmp_path, project, client=_AnswerClient())


class _AnswerClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return ""

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return json.dumps(
            {
                "id": "answer://a1",
                "question": "why?",
                "classification": "debugging",
                "assistance_level": "conceptual_explanation",
                "response": "Because the list state lives outside a ViewModel.",
                "citations": [],
                "uncertainty": False,
            }
        )


def _active_attempt(tmp_path, bus):
    store = ExamStore(tmp_path / "data")
    lifecycle = make_lifecycle(store, bus)
    return store, lifecycle.start(
        make_definition(),
        student_id="student://s1",
        project_id="project://p1",
    )


def test_cancelled_ask_is_recorded_but_not_counted(tmp_path):
    """RQ-EXM-005/006: a run the student aborts is recorded, never charged.

    ``AskAction`` must publish ``ASK_CANCELLED`` when the caller reports the run
    was aborted, so the attempt log carries a terminal event and the ask count
    stays at zero.
    """
    services = _ask_services(tmp_path)
    bus = services.event_bus
    store, attempt = _active_attempt(tmp_path, bus)
    services.context.exam_attempt_id = attempt.exam_attempt_id

    AskAction(services).run(
        "why does my LazyColumn not update?", is_cancelled=lambda: True
    )

    events = store.list_events(attempt.exam_attempt_id)
    types = [e.type for e in events]
    assert ExamEventType.ask_started in types
    assert ExamEventType.ask_cancelled in types
    assert ExamEventType.ask_completed not in types
    # The cancellation is a terminal event: nothing is left dangling.
    assert types[-1] is ExamEventType.ask_cancelled
    assert store.get(attempt.exam_attempt_id).ask_count == 0
    assert store.count_events(
        attempt.exam_attempt_id, ExamEventType.ask_completed
    ) == 0


def test_completed_ask_is_counted_when_not_cancelled(tmp_path):
    """The probe defaults to uncancelled, so a normal ask still counts."""
    services = _ask_services(tmp_path)
    bus = services.event_bus
    store, attempt = _active_attempt(tmp_path, bus)
    services.context.exam_attempt_id = attempt.exam_attempt_id

    AskAction(services).run("why does my LazyColumn not update?")

    events = store.list_events(attempt.exam_attempt_id)
    assert events[-1].type is ExamEventType.ask_completed
    assert store.get(attempt.exam_attempt_id).ask_count == 1


def test_cancelled_ask_is_not_charged_but_success_is(tmp_path):
    """One cancelled plus one completed ask: only the completed one counts."""
    services = _ask_services(tmp_path)
    bus = services.event_bus
    store, attempt = _active_attempt(tmp_path, bus)
    services.context.exam_attempt_id = attempt.exam_attempt_id
    action = AskAction(services)

    action.run("first question", is_cancelled=lambda: True)
    action.run("second question")

    assert store.get(attempt.exam_attempt_id).ask_count == 1
    assert store.count_events(attempt.exam_attempt_id, ExamEventType.ask_cancelled) == 1
    assert store.count_events(attempt.exam_attempt_id, ExamEventType.ask_completed) == 1