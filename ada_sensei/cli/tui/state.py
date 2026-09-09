"""Presentation-level state for the TUI (RQ-TUI-025).

Only presentation concerns live here (current view, visible messages, loading
state, pending input). Authoritative domain state remains in the shared
``SessionContext`` / application services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class View(str, Enum):
    CHAT = "chat"
    HELP = "help"
    EVALUATE = "evaluate"


@dataclass
class PresentationState:
    """Lightweight, non-authoritative UI state."""

    view: View = View.CHAT
    busy: bool = False
    status: str = "ready"
    messages: list[str] = field(default_factory=list)
    pending_input: str = ""
    cancelled: bool = False
    awaiting_name: bool = False
    user_name: str | None = None
    action: str = "ask"

    def push(self, text: str) -> None:
        self.messages.append(text)

    def set_busy(self, busy: bool, status: str | None = None) -> None:
        self.busy = busy
        if status is not None:
            self.status = status
