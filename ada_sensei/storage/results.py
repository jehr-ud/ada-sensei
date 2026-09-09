from __future__ import annotations

from ..models import EvaluationResult
from .json_store import JsonStore

KIND = "result"


class ResultStore:
    def __init__(self, data_dir: str) -> None:
        self.store = JsonStore(data_dir)

    @staticmethod
    def _urn(uri: str) -> str:
        return JsonStore.ensure_urn(KIND, uri)

    def save(self, result: EvaluationResult) -> EvaluationResult:
        self.store.write(result.id, JsonStore.to_payload(result))
        return result

    def get(self, uri: str) -> EvaluationResult | None:
        return JsonStore.from_payload(EvaluationResult, self.store.read(self._urn(uri)))

    def exists(self, uri: str) -> bool:
        return self.store.read(self._urn(uri)) is not None

    def list_ids(self) -> list[str]:
        return self.store.list_ids(KIND)
