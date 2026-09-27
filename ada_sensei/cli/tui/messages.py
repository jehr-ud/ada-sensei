"""TUI message carriers used to coordinate widgets with the app."""

from __future__ import annotations

from textual.message import Message

from .state import MessageKind, View


class ViewChanged(Message):
    """A screen/view was activated."""

    def __init__(self, view: View) -> None:
        super().__init__()
        self.view = view


class BusyChanged(Message):
    """A long-running operation started (busy=True) or finished (busy=False)."""

    def __init__(self, busy: bool, status: str) -> None:
        super().__init__()
        self.busy = busy
        self.status = status


class OutputReady(Message):
    """A rendered conversation entry is available to append to the log.

    ``kind`` is the presentation role of the entry (user, assistant, system, ...)
    so the log can render a distinguishable message per RQ-TUI-034. It is purely
    presentational and never affects application state.
    """

    def __init__(self, text: str, kind: MessageKind | str = MessageKind.SYSTEM) -> None:
        super().__init__()
        self.text = text
        self.kind = MessageKind(kind)
