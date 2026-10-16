"""Persistence for agent invocation records (spec 009)."""
from __future__ import annotations

import dataclasses
from pathlib import Path

from ..storage.json_store import JsonStore
from .contracts import AgentInvocationRecord


class AgentInvocationStore:
    """Persist AgentInvocationRecord under XDG data dir for observability and tests."""

    def __init__(self, data_dir: str | Path) -> None:
        self._store = JsonStore(data_dir)

    def append(self, record: AgentInvocationRecord) -> None:
        uri = f"learning://invocation-{record.id.replace('://', '_').replace('/', '_')}"
        payload = dataclasses.asdict(record)
        # datetime → iso string for JSON
        payload["created_at"] = record.created_at.isoformat()
        self._store.write(uri, payload)

    def get(self, invocation_id: str) -> AgentInvocationRecord | None:
        uid = invocation_id.replace("://", "_").replace("/", "_")
        uri = f"learning://invocation-{uid}"
        payload = self._store.read(uri)
        if payload is None:
            return None
        from datetime import datetime
        payload["created_at"] = datetime.fromisoformat(payload["created_at"])
        return AgentInvocationRecord(**payload)


__all__ = ["AgentInvocationStore"]
