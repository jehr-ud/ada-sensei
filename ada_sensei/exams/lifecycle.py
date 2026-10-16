"""Exam lifecycle: start, ask tracking, finish (RQ-EXM-003, RQ-EXM-004, RQ-EXM-007).

The state machine is explicit rather than implied by scattered flags:

    CREATED -> ACTIVE -> (ASK_STARTED -> ASK_COMPLETED|ASK_FAILED|ASK_CANCELLED)*
                     -> FINISH_REQUESTED -> EVALUATING -> COMPLETED

Only ``ExamLifecycle`` may move an attempt between states, and a completed attempt
accepts no further events, so the attempt log stays authoritative.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..events import AppEventBus
from ..models import Timestamps
from .docs import ExamDocs, ExamDocsWriter
from .events import ExamEventBridge
from .models import (
    ExamAttempt,
    ExamDefinition,
    ExamEvent,
    ExamEventType,
    ExamStateError,
    ExamStatus,
)
from .process import compute_duration_seconds, compute_overtime
from .store import ExamStore

#: Legal transitions (design.md §Exam lifecycle state machine).
TRANSITIONS: dict[ExamStatus, frozenset[ExamStatus]] = {
    ExamStatus.created: frozenset({ExamStatus.active}),
    ExamStatus.active: frozenset({ExamStatus.evaluating}),
    ExamStatus.evaluating: frozenset({ExamStatus.completed}),
    ExamStatus.completed: frozenset(),
}


class ExamLifecycle:
    """Owns one exam attempt from creation to completion."""

    def __init__(
        self,
        store: ExamStore,
        bus: AppEventBus,
        docs_writer: Callable[[], ExamDocsWriter | None] | None = None,
    ) -> None:
        self.store = store
        self.bus = bus
        #: Resolved lazily so constructing the lifecycle does not require a
        #: configured project; the project path is only known when an exam starts.
        self._docs_writer = docs_writer
        #: The one ask-event bridge for the live attempt. Exactly one may be
        #: subscribed, otherwise every ``/ask`` would be recorded twice and the
        #: count would be inflated (RQ-EXM-005, RQ-EXM-031).
        self._bridge: ExamEventBridge | None = None

    # -- start ------------------------------------------------------------

    def start(
        self,
        definition: ExamDefinition,
        *,
        student_id: str,
        project_id: str,
        project_root: str | Path | None = None,
        attempt_id: str | None = None,
        exercise_id: str | None = None,
        locale: str | None = None,
    ) -> ExamAttempt:
        """RQ-EXM-003: create the attempt, record EXAM_STARTED, create the docs."""
        if not student_id:
            raise ExamStateError("an exam requires an explicit student_id")
        if not project_id:
            raise ExamStateError("an exam requires an explicit project_id")

        from ..locale.models import SUPPORTED_LOCALES

        snapshot = locale if locale in SUPPORTED_LOCALES else None

        attempt = ExamAttempt(
            student_id=student_id,
            project_id=project_id,
            exam_id=definition.exam_id,
            attempt_id=attempt_id,
            exercise_id=exercise_id,
            started_at=Timestamps.now(),
            status=ExamStatus.created,
            allowed_duration_seconds=definition.allowed_duration_seconds,
            allowed_ask_count=definition.allowed_ask_count,
            rubric_ref=definition.rubric_ref,
            locale=snapshot,
        )
        docs: ExamDocs | None = None
        writer = self._docs_writer() if self._docs_writer is not None else None
        if writer is not None and project_root is not None:
            docs = writer.docs_for(definition.exam_id)
            writer.write_start_docs(definition, docs)
            attempt.docs_dir = str(docs.directory)

        # The statement is persisted now so finish scores what the student got.
        self.store.save_definition(definition)
        self._transition(attempt, ExamStatus.active)
        self.store.save(attempt)
        self._log(attempt, ExamEventType.exam_started)
        self.attach_bridge(attempt)
        return attempt

    # -- ask tracking -----------------------------------------------------

    def attach_bridge(self, attempt: ExamAttempt) -> ExamEventBridge:
        """Subscribe the single ask-event bridge for ``attempt``.

        Replaces any previous subscription, so starting a second exam can never
        leave two bridges counting the same ``/ask`` events.
        """
        self.detach_bridge()
        self._bridge = ExamEventBridge(attempt, self.bus, self.store)
        return self._bridge

    def detach_bridge(self) -> None:
        """Unsubscribe the ask bridge; a completed exam accepts no events."""
        if self._bridge is not None:
            self._bridge.detach()
            self._bridge = None

    @property
    def bridge_attached(self) -> bool:
        return self._bridge is not None

    # -- finish -----------------------------------------------------------

    def request_finish(
        self, attempt: ExamAttempt, confirmed: bool = False
    ) -> ExamAttempt:
        """RQ-EXM-004: finishing requires explicit confirmation."""
        if not confirmed:
            raise ExamStateError(
                "finishing an exam requires explicit confirmation"
            )
        self._log(attempt, ExamEventType.exam_finish_requested)
        self._transition(attempt, ExamStatus.evaluating)
        self.store.save(attempt)
        return attempt

    def finish(
        self,
        attempt: ExamAttempt,
        finished_at: datetime | None = None,
    ) -> ExamAttempt:
        """Stop the timer and complete the attempt (RQ-EXM-007).

        Duration is computed from the persisted timestamps only, never from a
        model claim or a terminal timestamp (RQ-EXM-031).
        """
        if attempt.status is not ExamStatus.evaluating:
            raise ExamStateError(
                f"cannot finish an attempt in state {attempt.status.value!r}; "
                "request_finish() must confirm first"
            )
        attempt.finished_at = finished_at or Timestamps.now()
        attempt.duration_seconds = compute_duration_seconds(
            attempt.started_at, attempt.finished_at
        )
        attempt.overtime_seconds = compute_overtime(
            attempt.duration_seconds, attempt.allowed_duration_seconds
        )
        self._transition(attempt, ExamStatus.completed)
        self.store.save(attempt)
        self._log(attempt, ExamEventType.exam_finished)
        return attempt

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _transition(attempt: ExamAttempt, target: ExamStatus) -> None:
        allowed = TRANSITIONS[attempt.status]
        if target not in allowed:
            raise ExamStateError(
                f"illegal exam transition {attempt.status.value!r} -> "
                f"{target.value!r}"
            )
        attempt.status = target

    def _log(self, attempt: ExamAttempt, event_type: ExamEventType) -> None:
        event = ExamEvent(
            exam_attempt_id=attempt.exam_attempt_id, type=event_type
        )
        self.store.append(event)
        attempt.event_ids.append(event.event_id)


__all__ = ["TRANSITIONS", "ExamLifecycle"]
