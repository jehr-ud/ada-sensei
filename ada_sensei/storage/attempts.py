from __future__ import annotations

from ..models import AssistanceLevel, Attempt, AttemptStatus
from .json_store import JsonStore

KIND = "attempt"


class AttemptStore:
    def __init__(self, data_dir: str) -> None:
        self.store = JsonStore(data_dir)

    @staticmethod
    def _urn(uri: str) -> str:
        return JsonStore.ensure_urn(KIND, uri)

    def save(self, attempt: Attempt) -> Attempt:
        self.store.write(attempt.id, JsonStore.to_payload(attempt))
        return attempt

    def get(self, uri: str) -> Attempt | None:
        return JsonStore.from_payload(Attempt, self.store.read(self._urn(uri)))

    def exists(self, uri: str) -> bool:
        return self.store.read(self._urn(uri)) is not None

    def mark_completed(self, uri: str) -> Attempt:
        attempt = self.get(uri)
        if attempt is None:
            raise KeyError(f"unknown attempt: {uri}")
        attempt.status = AttemptStatus.completed
        self.store.write(attempt.id, JsonStore.to_payload(attempt))
        return attempt

    def update_assistance(self, uri: str, level: AssistanceLevel) -> Attempt:
        attempt = self.get(uri)
        if attempt is None:
            raise KeyError(f"unknown attempt: {uri}")
        attempt.assistance_level = level
        self.store.write(attempt.id, JsonStore.to_payload(attempt))
        return attempt

    def add_hint(self, uri: str, hint: str) -> Attempt:
        attempt = self.get(uri)
        if attempt is None:
            raise KeyError(f"unknown attempt: {uri}")
        attempt.hints_used.append(hint)
        self.store.write(attempt.id, JsonStore.to_payload(attempt))
        return attempt
