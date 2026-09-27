"""Presentation-level state for the TUI (RQ-TUI-025).

Only presentation concerns live here (current view, visible messages, loading
state, pending input). Authoritative domain state remains in the shared
``SessionContext`` / application services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class View(StrEnum):
    CHAT = "chat"
    HELP = "help"
    EVALUATE = "evaluate"


class MessageKind(StrEnum):
    """Presentation role of a conversation entry (RQ-TUI-034).

    These are rendering roles only; they never carry domain meaning into the
    application layer and are never used to infer identity or compute scores.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    PRACTICE = "practice"
    EXERCISE = "exercise"
    HINT = "hint"
    EXAMPLE = "example"
    EVALUATION = "evaluation"
    ERROR = "error"


@dataclass
class PresentationState:
    """Lightweight, non-authoritative UI state."""

    view: View = View.CHAT
    busy: bool = False
    status: str = "Ready"
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
