from __future__ import annotations

from typing import Any

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
        payload = self.store.read(self._urn(uri))
        if payload is None:
            return None
        return JsonStore.from_payload(self._model_for(payload), payload)

    @staticmethod
    def _model_for(payload: dict[str, Any]) -> type[EvaluationResult]:
        """Read exam results back as ``ExamResult``.

        ``ExamResult`` extends ``EvaluationResult``; without this dispatch a
        persisted exam result would silently lose its exam identity, process
        metrics, and grade pair on read (RQ-EXM-026). The import is deferred to
        keep the storage layer free of a hard dependency on the exam package.
        """
        if payload.get("exam_attempt_id"):
            from ..exams.models import ExamResult

            return ExamResult
        return EvaluationResult

    def exists(self, uri: str) -> bool:
        return self.store.read(self._urn(uri)) is not None

    def list_ids(self) -> list[str]:
        return self.store.list_ids(KIND)
