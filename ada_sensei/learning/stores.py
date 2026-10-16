"""XDG-based JSON stores for learning-path domain objects (spec 008)."""
from __future__ import annotations

from pathlib import Path

from ..storage.json_store import JsonStore
from .models import (
    LearningEvent,
    LearningProfile,
    MasteryAssessment,
    ProgressionDecision,
)


class LearningProfileStore:
    def __init__(self, data_dir: str | Path) -> None:
        self._store = JsonStore(data_dir)

    def get(self, student_id: str) -> LearningProfile | None:
        uri = f"learning://profile-{_sanitize(student_id)}"
        payload = self._store.read(uri)
        return JsonStore.from_payload(LearningProfile, payload)

    def save(self, profile: LearningProfile) -> None:
        uri = f"learning://profile-{_sanitize(profile.student_id)}"
        self._store.write(uri, JsonStore.to_payload(profile))


class MasteryAssessmentStore:
    def __init__(self, data_dir: str | Path) -> None:
        self._store = JsonStore(data_dir)

    def save(self, assessment: MasteryAssessment) -> None:
        self._store.write(assessment.id, JsonStore.to_payload(assessment))

    def get(self, assessment_id: str) -> MasteryAssessment | None:
        payload = self._store.read(assessment_id)
        return JsonStore.from_payload(MasteryAssessment, payload)

    def list_for_student(self, student_id: str, stage_id: str) -> list[MasteryAssessment]:
        results: list[MasteryAssessment] = []
        for uid in self._store.list_ids("learning"):
            uri = f"learning://{uid}"
            payload = self._store.read(uri)
            if payload is None:
                continue
            obj = JsonStore.from_payload(MasteryAssessment, payload)
            if (
                obj is not None
                and obj.student_id == student_id
                and obj.stage_id == stage_id
            ):
                results.append(obj)
        return results


class ProgressionDecisionStore:
    def __init__(self, data_dir: str | Path) -> None:
        self._store = JsonStore(data_dir)

    def save(self, decision: ProgressionDecision) -> None:
        self._store.write(decision.decision_id, JsonStore.to_payload(decision))

    def get(self, decision_id: str) -> ProgressionDecision | None:
        payload = self._store.read(decision_id)
        return JsonStore.from_payload(ProgressionDecision, payload)

    def get_latest(self, student_id: str, stage_id: str) -> ProgressionDecision | None:
        latest: ProgressionDecision | None = None
        for uid in self._store.list_ids("decision"):
            uri = f"decision://{uid}"
            payload = self._store.read(uri)
            if payload is None:
                continue
            obj = JsonStore.from_payload(ProgressionDecision, payload)
            if (
                obj is not None
                and obj.student_id == student_id
                and obj.from_stage_id == stage_id
            ):
                if latest is None or obj.created_at > latest.created_at:
                    latest = obj
        return latest


class LearningEventStore:
    def __init__(self, data_dir: str | Path) -> None:
        self._store = JsonStore(data_dir)

    def append(self, event: LearningEvent) -> None:
        self._store.write(event.id, JsonStore.to_payload(event))

    def list_for_student(
        self, student_id: str, limit: int = 50
    ) -> list[LearningEvent]:
        results: list[LearningEvent] = []
        for uid in self._store.list_ids("learning"):
            uri = f"learning://{uid}"
            payload = self._store.read(uri)
            if payload is None:
                continue
            obj = JsonStore.from_payload(LearningEvent, payload)
            if obj is not None and obj.student_id == student_id:
                results.append(obj)
        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]


def _sanitize(value: str) -> str:
    """Replace URN-unsafe characters for use as a storage key."""
    return value.replace("://", "_").replace("/", "_").replace(" ", "_")


__all__ = [
    "LearningEventStore",
    "LearningProfileStore",
    "MasteryAssessmentStore",
    "ProgressionDecisionStore",
]
