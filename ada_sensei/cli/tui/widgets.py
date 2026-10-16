"""TUI widgets (RQ-TUI-004, RQ-TUI-032).

All widgets are presentation-only. They render values supplied by the
application/session layer; they never calculate scores, select AI models, or
infer student identity (RQ-TUI-002, RQ-TUI-032).
"""

from __future__ import annotations

import contextlib

from textual import events
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Select, Static, TextArea


class ActionSelector(Select):
    """Action dropdown that activates `Change language` on Enter (RQ-LNG-015).

    The base ``Select`` consumes Enter to toggle its overlay, so keyboard
    users highlighting an action could never run it from the selector itself.
    When the committed value's stable id is ``"language"``, Enter posts
    :class:`LanguageRequested` instead of opening the overlay, and the app
    opens the same ``LanguageList`` used by first-run welcome. Matching uses
    the stable option value, never the localized label. All other values keep
    native dropdown behavior.
    """

    class LanguageRequested(Message):
        """Enter pressed while the selector value is the `language` action."""

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter" and self.value == "language":
            event.stop()
            event.prevent_default()
            self.post_message(self.LanguageRequested())
            return
        await super()._on_key(event)


class SessionBar(Static):
    """Header showing session context: app version, student, project, stage."""

    def refresh_context(
        self,
        student: str | None,
        project: str | None,
        *,
        version: str | None = None,
        stage_text: str | None = None,
    ) -> None:
        bits = []
        if student:
            bits.append(f"student: {student}")
        if project:
            bits.append(f"project: {project}")
        if stage_text:
            bits.append(stage_text)
        suffix = "  |  " + "  |  ".join(bits) if bits else ""
        prefix = f"ADA Sensei v{version}" if version else "ADA Sensei"
        self.update(f"{prefix}{suffix}")


class SessionFooter(Static):
    """Persistent bottom session footer (RQ-TUI-032).

    Shows the authoritative session metadata supplied by the application layer:
    student name, current score, active AI model, current action, and operation
    status. Unavailable values are rendered as ``—``.

    While an exam is active it also shows the exam elapsed time and the
    ``/ask`` count. Both are read from the persisted attempt and its event log
    via ``CommandRouter.exam_status()``; the footer never counts asks or times
    an exam itself (RQ-EXM-005, RQ-EXM-007, RQ-EXM-031).
    """

    EMPTY = "—"

    def _fmt(self, value) -> str:
        return f"{value}" if value not in (None, "") else self.EMPTY

    @staticmethod
    def _mmss(seconds) -> str:
        seconds = int(seconds)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    @classmethod
    def _exam_text(cls, status) -> str:
        if status is None:
            return ""
        label = "Exam done" if status.is_completed else "Exam"
        elapsed = (
            cls._mmss(status.duration_seconds)
            if status.duration_seconds is not None
            else cls.EMPTY
        )
        if status.allowed_duration_seconds is not None:
            allowed = cls._mmss(status.allowed_duration_seconds)
            elapsed = f"{elapsed}/{allowed}"
        asks = str(status.ask_count)
        if status.allowed_ask_count is not None:
            asks = f"{asks}/{status.allowed_ask_count}"
        return f"{label} {elapsed} | Asks {asks}"

    def update_session(
        self,
        *,
        student: str | None,
        score: float | None,
        model: str | None,
        action: str | None,
        status: str | None = None,
        exam=None,
        stage: str | None = None,
        version: str | None = None,
        locale: str | None = None,
    ) -> None:
        parts = [
            f"Student: {self._fmt(student)}",
            f"Score: {self._fmt(score)}",
            f"AI: {self._fmt(model)}",
            f"Action: {self._fmt(action)}",
        ]
        if stage:
            parts.append(stage)
        if locale:
            parts.append(f"Lang: {locale}")
        if version:
            parts.append(f"v{version}")
        if status:
            parts.append(f"{self._fmt(status)}")
        exam_text = self._exam_text(exam)
        if exam_text:
            parts.append(exam_text)
        self.update(" | ".join(parts))


class PromptArea(TextArea):
    """Editable multi-line input where Enter runs the selected action.

    Per RQ-TUI-021 and RQ-TUI-030, Enter executes the currently selected action
    and Shift+Enter inserts a new line. The base ``TextArea`` inserts a new line
    on Enter, so Enter is consumed here and re-posted as :class:`PromptSubmitted`
    for the App to execute. Shift+Enter is declared as a widget binding so the
    Footer visibly communicates the gesture.

    Per RQ-TUI-039, Up/Down browse the session input history when the caret is
    at the relevant boundary (Up at the first line, or while already
    browsing). Otherwise Up/Down keep their normal cursor behavior; the base
    ``TextArea`` handlers are never swallowed globally. The first edit to a
    recalled prompt exits browsing while keeping the text editable.
    """

    BINDINGS = [
        Binding("shift+enter", "insert_newline", "New line"),
    ]

    #: Session input history bound by the App; ``None`` disables recall.
    #: Named ``input_history`` to avoid colliding with TextArea's internal
    #: undo ``history`` (EditHistory).
    input_history = None

    class PromptSubmitted(Message):
        """Enter was pressed and the current text should be executed."""

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.PromptSubmitted())
            return
        if event.key in ("up", "down") and self._history_key(event.key):
            event.stop()
            event.prevent_default()
            return
        if (
            self.input_history is not None
            and self.input_history.browsing
            and event.key != "enter"
        ):
            # Any other key edits or moves away: exit browsing deterministically
            # while retaining the recalled text for editing.
            self.input_history.reset()
        await super()._on_key(event)

    async def _on_paste(self, event: events.Paste) -> None:
        if self.input_history is not None and self.input_history.browsing:
            self.input_history.reset()
        await super()._on_paste(event)

    def _history_key(self, key: str) -> bool:
        """Handle Up/Down for history recall; True when consumed."""
        history = self.input_history
        if history is None:
            return False
        if key == "up":
            if history.browsing:
                recalled = history.older()
            elif self.cursor_at_first_line:
                recalled = history.begin(self.text or "")
            else:
                return False
            if recalled is None:
                return False
            self._recall_text(recalled)
            return True
        if key == "down":
            if not history.browsing:
                return False
            self._recall_text(history.newer())
            return True
        return False

    def _recall_text(self, text: str) -> None:
        """Replace the input with recalled text and park the caret at the end."""
        self.text = text
        lines = text.split("\n")
        with contextlib.suppress(Exception):
            self.move_cursor((len(lines) - 1, len(lines[-1])))

    def action_insert_newline(self) -> None:
        self._restart_blink()
        if self.read_only:
            return
        start, end = self.selection
        self._replace_via_keyboard("\n", start, end)


class StatusBar(Static):
    """Fallback footer/status area (RQ-TUI-004).

    Kept for backward compatibility; the richer :class:`SessionFooter` is the
    primary persistent session line.
    """


class ActionGuide(Static):
    """Persistent guidance for the focused selector action (spec 0011 §3).

    Presentation-only: renders the localized description, expected input,
    outcome, and activation hint supplied by the application layer
    (``CommandRouter.describe_action``). It never computes guidance itself.
    """


class LanguageList(Static):
    """Dedicated language-selection list (spec 0010, RQ-LNG-004/005).

    Presentation-only: renders the ``LanguageSelection`` cursor state owned by
    the app (options, ``>`` focus marker, title, key hints). Widget-scoped
    bindings keep Up/Down/Enter/Esc/q local to the list so TextArea editing
    is unaffected. Persistence and refresh happen in the app/router paths.
    """

    can_focus = True

    BINDINGS = [
        Binding("up", "cursor_up", "Move up"),
        Binding("down", "cursor_down", "Move down"),
        Binding("enter", "confirm", "Select"),
        Binding("escape", "cancel", "Cancel"),
        Binding("q", "cancel", "Cancel"),
    ]

    class FocusMoved(Message):
        """Cursor moved; carries the newly focused locale code."""

        def __init__(self, locale: str) -> None:
            super().__init__()
            self.locale = locale

    class Confirmed(Message):
        """Explicit confirmation; carries the selected stable locale code."""

        def __init__(self, locale: str) -> None:
            super().__init__()
            self.locale = locale

    class Cancelled(Message):
        """Cancellation without any change."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selection = None
        self._title = ""
        self._hints = ""

    @property
    def selection(self):
        return self._selection

    def show(self, selection, *, title: str = "", hints: str = "") -> None:
        self._selection = selection
        self._title = title
        self._hints = hints
        self.styles.display = "block"
        self.update(self._render_text())
        with contextlib.suppress(Exception):
            self.focus()

    def hide(self) -> None:
        self._selection = None
        self.styles.display = "none"
        self.update("")

    @property
    def is_open(self) -> bool:
        return self._selection is not None

    def _render_text(self):
        from rich.text import Text

        text = Text()
        if self._title:
            text.append(self._title + "\n", style="bold")
            text.append("\n")
        selection = self._selection
        if selection is not None:
            for i, (_code, label) in enumerate(selection.options):
                marker = "> " if i == selection.index else "  "
                style = "bold reverse" if i == selection.index else ""
                text.append(f"{marker}{label}\n", style=style)
        if self._hints:
            text.append("\n" + self._hints, style="dim")
        return text

    def _move(self, delta: int) -> None:
        selection = self._selection
        if selection is None:
            return
        if delta < 0:
            selection.move_up()
        else:
            selection.move_down()
        self.update(self._render_text())
        self.post_message(self.FocusMoved(selection.focused_locale))

    def action_cursor_up(self) -> None:
        self._move(-1)

    def action_cursor_down(self) -> None:
        self._move(1)

    def action_confirm(self) -> None:
        if self._selection is None:
            return
        self.post_message(self.Confirmed(self._selection.confirm()))

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())


class StatusIndicator(Static):
    """Transient in-conversation processing indicator.

    Shows a lightweight, animated ``Running…``/``Evaluating…`` line while a
    long-running operation is active. It is strictly transient: the canonical
    status lives on the presentation state (machine-readable ``Running``) and
    this widget only mirrors the animated display. It holds no domain data.
    """


class Divider(Horizontal):
    pass
