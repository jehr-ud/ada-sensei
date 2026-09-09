"""TUI screens (RQ-TUI-004)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog

from .widgets import PromptArea, SessionBar, SessionFooter


class MainScreen(Screen):
    """Primary conversation screen: header, log, input, status."""

    BINDINGS = []

    def compose(self) -> ComposeResult:
        yield SessionBar(id="session-bar")
        yield RichLog(id="log", markup=True, wrap=True)
        yield PromptArea("", id="input")
        yield SessionFooter(id="session-footer")
        yield Footer()
        yield Header()