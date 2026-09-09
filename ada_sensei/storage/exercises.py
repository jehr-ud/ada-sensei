from __future__ import annotations

from ..models import Exercise
from .json_store import JsonStore

KIND = "exercise"


class ExerciseStore:
    def __init__(self, data_dir: str) -> None:
        self.store = JsonStore(data_dir)

    @staticmethod
    def _urn(uri: str) -> str:
        return JsonStore.ensure_urn(KIND, uri)

    def save(self, exercise: Exercise) -> Exercise:
        self.store.write(exercise.id, JsonStore.to_payload(exercise))
        return exercise

    def get(self, uri: str) -> Exercise | None:
        return JsonStore.from_payload(Exercise, self.store.read(self._urn(uri)))

    def exists(self, uri: str) -> bool:
        return self.store.read(self._urn(uri)) is not None

    def list_ids(self) -> list[str]:
        return self.store.list_ids(KIND)
