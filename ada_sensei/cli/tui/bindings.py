"""Key bindings for the TUI (RQ-TUI-021).

Textual handles most of these via ``BINDINGS`` on the App; we centralize the
shared binding metadata here so tests can assert them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Binding:
    key: str
    action: str
    description: str


BINDINGS: tuple[Binding, ...] = (
    Binding("ctrl+q", "quit", "Quit"),
    Binding("ctrl+d", "quit", "Quit (clean exit)"),
    Binding("ctrl+c", "cancel_operation", "Cancel current operation"),
    Binding("enter", "submit", "Enter Run"),
    Binding("f2", "show_help", "Help"),
)
