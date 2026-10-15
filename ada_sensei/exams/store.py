"""Persistence for exam attempts and the authoritative event log.

Backed by the shared ``JsonStore`` so exam data lives beside every other ADA
Sensei record. ``ExamStore.save`` is the enforcement point for RQ-EXM-004: once
an attempt is completed, only administrative metadata may change, and any other
difference raises instead of being written.
"""

from __future__ import annotations

from pathlib import Path

from ..storage.json_store import JsonStore
from .models import (
    ExamAttempt,
    ExamAttemptImmutableError,
    ExamDefinition,
    ExamEvent,
    ExamEventType,
)

ATTEMPT_KIND = "exam_attempt"
EVENT_KIND = "exam_event"
DEFINITION_KIND = "exam_definition"


class ExamStore:
    """Durable exam attempts plus their append-only event log."""

    def __init__(self, data_dir: str | Path) -> None:
        self.store = JsonStore(data_dir)

    # -- attempts ---------------------------------------------------------

    @staticmethod
    def _attempt_urn(exam_attempt_id: str) -> str:
        return JsonStore.ensure_urn(ATTEMPT_KIND, exam_attempt_id)

    def save(self, attempt: ExamAttempt) -> ExamAttempt:
        """Persist an attempt, refusing post-completion content changes."""
        uri = self._attempt_urn(attempt.exam_attempt_id)
        existing = self.get(attempt.exam_attempt_id)
        if existing is not None and existing.is_completed:
            self._assert_only_administrative_change(existing, attempt)
        self.store.write(uri, JsonStore.to_payload(attempt))
        return attempt

    @staticmethod
    def _assert_only_administrative_change(
        existing: ExamAttempt, incoming: ExamAttempt
    ) -> None:
        before = existing.substantive()
        after = incoming.substantive()
        if before == after:
            return
        changed = sorted(
            key
            for key in set(before) | set(after)
            if before.get(key) != after.get(key)
        )
        raise ExamAttemptImmutableError(
            f"exam attempt {existing.exam_attempt_id} is completed; only "
            "administrative metadata may change, but these fields differ: "
            f"{changed}"
        )

    def get(self, exam_attempt_id: str) -> ExamAttempt | None:
        payload = self.store.read(self._attempt_urn(exam_attempt_id))
        return JsonStore.from_payload(ExamAttempt, payload)

    def exists(self, exam_attempt_id: str) -> bool:
        return self.store.path_for(self._attempt_urn(exam_attempt_id)).exists()

    def list_ids(self) -> list[str]:
        return self.store.list_ids(ATTEMPT_KIND)

    def active_for(self, exam_attempt_id: str | None) -> ExamAttempt | None:
        if not exam_attempt_id:
            return None
        attempt = self.get(exam_attempt_id)
        return attempt if attempt is not None and attempt.is_active else None

    # -- events -----------------------------------------------------------

    @staticmethod
    def _event_urn(event_id: str) -> str:
        return JsonStore.ensure_urn(EVENT_KIND, event_id)

    def append(self, event: ExamEvent) -> ExamEvent:
        """Append one event. The log is append-only; nothing is rewritten."""
        self.store.write(self._event_urn(event.event_id), JsonStore.to_payload(event))
        return event

    def get_event(self, event_id: str) -> ExamEvent | None:
        payload = self.store.read(self._event_urn(event_id))
        return JsonStore.from_payload(ExamEvent, payload)

    def list_events(self, exam_attempt_id: str) -> list[ExamEvent]:
        """The attempt log in timestamp order; the authoritative record."""
        events = [
            event
            for event in (
                JsonStore.from_payload(ExamEvent, self.store.read(self._event_urn(eid)))
                for eid in self.store.list_ids(EVENT_KIND)
            )
            if event is not None and event.exam_attempt_id == exam_attempt_id
        ]
        return sorted(events, key=lambda e: (e.timestamp, e.event_id))

    def count_events(
        self, exam_attempt_id: str, event_type: ExamEventType
    ) -> int:
        return sum(
            1
            for event in self.list_events(exam_attempt_id)
            if event.type is event_type
        )

    # -- definitions ------------------------------------------------------

    @staticmethod
    def _definition_urn(exam_id: str) -> str:
        return JsonStore.ensure_urn(DEFINITION_KIND, exam_id)

    def save_definition(self, definition: ExamDefinition) -> ExamDefinition:
        """Persist the authoritative statement the student was given.

        The definition is written at start time and read again at finish time, so
        the score always reflects the statement that was issued. An instructor
        editing the source file mid-exam cannot retroactively change what the
        student was assessed against (spec.md §Exam definition).
        """
        self.store.write(
            self._definition_urn(definition.exam_id),
            JsonStore.to_payload(definition),
        )
        return definition

    def get_definition(self, exam_id: str) -> ExamDefinition | None:
        payload = self.store.read(self._definition_urn(exam_id))
        return JsonStore.from_payload(ExamDefinition, payload)


__all__ = [
    "ATTEMPT_KIND",
    "DEFINITION_KIND",
    "EVENT_KIND",
    "ExamStore",
]
