"""Persist locale preference per student under XDG data dir (spec 0010)."""
from __future__ import annotations

from pathlib import Path

from ..storage.json_store import JsonStore
from .models import LocalePreference


class LocalePreferenceStore:
    def __init__(self, data_dir: str | Path) -> None:
        self._store = JsonStore(data_dir)

    def get(self, student_id: str) -> LocalePreference | None:
        uri = f"learning://locale-{_sanitize(student_id)}"
        payload = self._store.read(uri)
        return JsonStore.from_payload(LocalePreference, payload)

    def save(self, student_id: str, pref: LocalePreference) -> None:
        uri = f"learning://locale-{_sanitize(student_id)}"
        self._store.write(uri, JsonStore.to_payload(pref))


def _sanitize(value: str) -> str:
    return value.replace("://", "_").replace("/", "_").replace(" ", "_")


__all__ = ["LocalePreferenceStore"]
