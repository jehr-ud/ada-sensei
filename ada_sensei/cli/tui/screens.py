"""TUI screens (RQ-TUI-004)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog

from .widgets import SessionBar, StatusBar


class MainScreen(Screen):
    """Primary conversation screen: header, log, prompt, status."""

    BINDINGS = []

    def compose(self) -> ComposeResult:
        yield SessionBar(id="session-bar")
        yield RichLog(id="log", markup=True, wrap=True)
        with Horizontal(id="prompt-row"):
            yield Input(placeholder="type a command (/help)", id="input")
        yield StatusBar(id="status-bar")
        yield Footer()
        yield Header()
