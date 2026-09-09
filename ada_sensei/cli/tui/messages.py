"""TUI message carriers used to coordinate widgets with the app."""

from __future__ import annotations

from textual.message import Message

from .state import View


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
    """A rendered output fragment is available to append to the log."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text
