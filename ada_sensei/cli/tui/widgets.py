"""TUI widgets (RQ-TUI-004)."""

from __future__ import annotations

from textual.containers import Horizontal
from textual.widgets import Static


class SessionBar(Static):
    """Header showing session context: student and active project."""

    def refresh_context(self, student: str | None, project: str | None) -> None:
        bits = []
        if student:
            bits.append(f"student: {student}")
        if project:
            bits.append(f"project: {project}")
        suffix = "  |  " + "  |  ".join(bits) if bits else ""
        self.update(f"ADA Sensei{suffix}")


class StatusBar(Static):
    """Footer/status area (RQ-TUI-004)."""


class Divider(Horizontal):
    pass
