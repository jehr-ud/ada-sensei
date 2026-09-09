"""Persistence of the last used student name (TUI welcome flow).

The name is stored separately from the ``StudentProfile`` so the TUI can
remember which identity was used last and start a new run without re-asking
(RQ-TUI-029). This is a convenience for the welcome flow only; it SHALL NOT be
used to infer identity (RQ-CLI-006, RQ-TUI-007, ADR-015).
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

FILE_NAME = "last_student.json"


class LastStudentStore:
    """Read/write the last used student name under the data directory."""

    def __init__(self, data_dir: str | Path) -> None:
        self.path = Path(data_dir) / FILE_NAME

    def load(self) -> str | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        name = data.get("name")
        return name.strip() if isinstance(name, str) and name.strip() else None

    def save(self, name: str) -> None:
        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=target.parent, prefix=target.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"name": name}, fh, ensure_ascii=False)
            os.replace(tmp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise