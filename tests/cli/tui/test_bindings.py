"""Keyboard interaction requirements (RQ-TUI-021) and shared bindings.

Enter executes the selected action; Shift+Enter inserts a new line (handled by
the PromptArea widget); Ctrl+C cancels; Ctrl+D quits.
"""

from __future__ import annotations

from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.bindings import BINDINGS

ACTION_KEYS = {b.action for b in BINDINGS}


def test_quit_binding_present():
    assert "quit" in ACTION_KEYS


def test_cancel_binding_present():
    assert "cancel_operation" in ACTION_KEYS


def test_help_binding_present():
    assert "show_help" in ACTION_KEYS


def test_enter_binding_present():
    assert any(b.action == "submit" and b.key == "enter" for b in BINDINGS)


def test_ctrl_enter_not_bound():
    assert not any(b.key == "ctrl+enter" for b in BINDINGS)


def test_app_declares_bindings():
    keys = [b.key for b in AdaSenseiTUI.BINDINGS]
    assert "ctrl+q" in keys
    assert "ctrl+c" in keys
    assert "enter" in keys
    assert "ctrl+enter" not in keys