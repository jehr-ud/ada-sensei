"""Exam attempt log and ``/ask`` tracking (RQ-EXM-005, RQ-EXM-006, RQ-EXM-031).

The attempt log is authoritative. ``ExamEventBridge`` subscribes to the ask
events published by ``AskAction`` and writes ``ExamEvent`` records; the ask count
is always *derived* by counting successful events in the log, never read from a
total in any model response.
"""

from __future__ import annotations

from typing import Protocol

from ..events import (
    ASK_CANCELLED,
    ASK_COMPLETED,
    ASK_FAILED,
    ASK_STARTED,
    AppEvent,
    AppEventBus,
)
from .models import (
    ASK_SUCCESS_EVENTS,
    ExamAttempt,
    ExamEvent,
    ExamEventType,
    ExamStateError,
)

#: Application event name -> exam event type. Only the successful ask counts.
EVENT_MAP = {
    ASK_STARTED: ExamEventType.ask_started,
    ASK_COMPLETED: ExamEventType.ask_completed,
    ASK_FAILED: ExamEventType.ask_failed,
    ASK_CANCELLED: ExamEventType.ask_cancelled,
}


class ExamEventLog(Protocol):
    """The persistence surface the bridge needs; implemented by ``ExamStore``."""

    def append(self, event: ExamEvent) -> ExamEvent: ...

    def list_events(self, exam_attempt_id: str) -> list[ExamEvent]: ...


class AttemptSink(Protocol):
    """Optional surface used to persist the recounted ask total."""

    def save(self, attempt: ExamAttempt) -> ExamAttempt: ...


class ExamEventBridge:
    """Turns application events into exam events for the active attempt.

    The bridge is attached to one attempt and refuses to record anything once the
    attempt is completed (spec.md: a completed attempt cannot accept new ask
    events).
    """

    def __init__(
        self,
        attempt: ExamAttempt,
        bus: AppEventBus,
        log: ExamEventLog | None = None,
    ) -> None:
        self.attempt = attempt
        self.bus = bus
        self.log = log
        # ``ExamStore`` also satisfies ``AttemptSink``; a caller may pass a
        # read-only log, in which case the total is recomputed from the log
        # whenever it is read rather than cached.
        self._attempts: AttemptSink | None = log if hasattr(log, "save") else None
        self._subscriptions: list[tuple[str, object]] = []
        #: Events recorded by this bridge, so the ask count stays derived from
        #: events even when no persistent log was supplied.
        self._recorded: list[ExamEvent] = []
        self.attach()

    def attach(self) -> None:
        for event_name in EVENT_MAP:
            handler = self._handler_for(event_name)
            self.bus.subscribe(event_name, handler)
            self._subscriptions.append((event_name, handler))

    def detach(self) -> None:
        for event_name, handler in self._subscriptions:
            self.bus.unsubscribe(event_name, handler)  # type: ignore[arg-type]
        self._subscriptions.clear()

    def _handler_for(self, event_name: str):
        def handler(event: AppEvent) -> None:
            self.handle(event_name, event)

        return handler

    # -- event recording --------------------------------------------------

    def handle(self, event_name: str, event: AppEvent) -> ExamEvent | None:
        """Record an application event; ignored when no exam is active."""
        exam_event_type = EVENT_MAP.get(event_name)
        if exam_event_type is None or not self.attempt.is_active:
            return None
        return self.record(
            exam_event_type,
            question_id=event.get("question_id"),
            duration_ms=event.get("duration_ms"),
            metadata=dict(event.payload),
        )

    def record(
        self,
        event_type: ExamEventType,
        *,
        question_id: str | None = None,
        duration_ms: int | None = None,
        metadata: dict | None = None,
    ) -> ExamEvent:
        """Append one event, then recount asks from the log (RQ-EXM-005/006)."""
        if self.attempt.is_completed:
            raise ExamStateError(
                f"exam attempt {self.attempt.exam_attempt_id} is completed; "
                "no further events are accepted"
            )
        exam_event = ExamEvent(
            exam_attempt_id=self.attempt.exam_attempt_id,
            type=event_type,
            question_id=question_id,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        if self.log is not None:
            self.log.append(exam_event)
        self._recorded.append(exam_event)
        self.attempt.event_ids.append(exam_event.event_id)
        self.attempt.ask_count = self.count_asks()
        if self._attempts is not None:
            # The count is persisted immediately: the attempt log is the
            # authoritative record, and a later read must not fall back to a
            # stale total (RQ-EXM-005, RQ-EXM-031).
            self._attempts.save(self.attempt)
        return exam_event

    def count_asks(self) -> int:
        """Successful asks recorded for this attempt, from the log itself."""
        if self.log is None:
            return sum(
                1 for event in self._recorded if event.type in ASK_SUCCESS_EVENTS
            )
        return sum(
            1
            for event in self.log.list_events(self.attempt.exam_attempt_id)
            if event.type in ASK_SUCCESS_EVENTS
        )


__all__ = [
    "EVENT_MAP",
    "AttemptSink",
    "ExamEventBridge",
    "ExamEventLog",
]
