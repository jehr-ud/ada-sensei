"""Presentation/domain state boundary (RQ-TUI-025).

Presentation state tracks the view, busy flag, and visible messages. It must not
duplicate authoritative domain state, which lives in SessionContext.
"""

from __future__ import annotations

from ada_sensei.cli.tui.state import PresentationState, View


def test_presentation_state_holds_ui_only():
    state = PresentationState()
    state.push("hello")
    state.set_busy(True, "running")
    assert state.view == View.CHAT
    assert state.busy is True
    assert state.status == "running"
    assert state.messages == ["hello"]
    # No student/project/exercise domain fields here.
    assert not hasattr(state, "student_id")
    assert not hasattr(state, "exercise_id")


def test_view_transitions():
    state = PresentationState()
    state.view = View.HELP
    assert state.view == View.HELP


def test_cancelled_flag():
    state = PresentationState()
    state.cancelled = True
    assert state.cancelled is True
