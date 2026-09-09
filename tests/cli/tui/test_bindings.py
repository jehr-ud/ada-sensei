"""Keyboard interaction requirements (RQ-TUI-021) and shared bindings."""

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


def test_app_declares_bindings():
    keys = [b.key for b in AdaSenseiTUI.BINDINGS]
    assert "ctrl+q" in keys
    assert "ctrl+c" in keys
