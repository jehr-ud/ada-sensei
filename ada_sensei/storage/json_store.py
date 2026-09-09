from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..urns import URN

SCHEMA_VERSION = 1

_ROUTING: dict[str, str] = {
    "project": "projects",
    "student": "history",
    "exercise": "exercises",
    "attempt": "attempts",
    "result": "results",
    "example": "examples",
    "answer": "answers",
    "learning": "learning",
    "session": "sessions",
}


class JsonStore:
    def __init__(
        self, data_dir: str | Path, schema_version: int = SCHEMA_VERSION
    ) -> None:
        self.data_dir = Path(data_dir)
        self.schema_version = schema_version

    def _kind_dir(self, kind: str) -> Path:
        return self.data_dir / _ROUTING.get(kind, kind)

    def path_for(self, uri: str) -> Path:
        kind, uid = URN.parse(uri)
        return self._kind_dir(kind) / f"{uid}.json"

    @staticmethod
    def ensure_urn(kind: str, value: str) -> str:
        if value.startswith(f"{kind}://"):
            return value
        return f"{kind}://{value.lstrip('/')}"

    @staticmethod
    def to_payload(model: Any) -> dict[str, Any]:
        return model.model_dump(mode="json")

    @staticmethod
    def from_payload(
        model_cls: type[Any], payload: dict[str, Any] | None
    ) -> Any | None:
        if payload is None:
            return None
        return model_cls.model_validate(payload)

    def write(self, uri: str, payload: dict[str, Any]) -> None:
        doc = {"schema": self.schema_version, "id": uri, "data": payload}
        target = self.path_for(uri)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=target.parent, prefix=target.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise

    def read(self, uri: str) -> dict[str, Any] | None:
        target = self.path_for(uri)
        if not target.exists():
            return None
        try:
            doc = json.loads(target.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        if doc.get("schema") != self.schema_version:
            return None
        return doc.get("data")

    def delete(self, uri: str) -> bool:
        target = self.path_for(uri)
        if target.exists():
            target.unlink()
            return True
        return False

    def list_ids(self, kind: str, directory: str | None = None) -> list[str]:
        target = self._kind_dir(directory or kind)
        if not target.exists():
            return []
        return [p.stem for p in target.glob("*.json") if p.suffix == ".json"]
