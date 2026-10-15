"""TUI widgets (RQ-TUI-004, RQ-TUI-032).

All widgets are presentation-only. They render values supplied by the
application/session layer; they never calculate scores, select AI models, or
infer student identity (RQ-TUI-002, RQ-TUI-032).
"""

from __future__ import annotations

from textual import events
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Static, TextArea


class SessionBar(Static):
    """Header showing session context: student and active project."""

    def refresh_context(self, student: str | None, project: str | None) -> None:
        bits = []
        if student:
            bits.append(f"student: {student}")
        if project:
            bits.append(f"project: {project}")
        suffix = "  |  " + "  |  ".join(bits) if bits else ""
        self.update(f"ADA Sensei{suffix}")


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
    ) -> None:
        parts = [
            f"Student: {self._fmt(student)}",
            f"Score: {self._fmt(score)}",
            f"AI: {self._fmt(model)}",
            f"Action: {self._fmt(action)}",
        ]
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
    """

    BINDINGS = [
        Binding("shift+enter", "insert_newline", "New line"),
    ]

    class PromptSubmitted(Message):
        """Enter was pressed and the current text should be executed."""

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.PromptSubmitted())
            return
        await super()._on_key(event)

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


class StatusIndicator(Static):
    """Transient in-conversation processing indicator.

    Shows a lightweight, animated ``Running…``/``Evaluating…`` line while a
    long-running operation is active. It is strictly transient: the canonical
    status lives on the presentation state (machine-readable ``Running``) and
    this widget only mirrors the animated display. It holds no domain data.
    """


class Divider(Horizontal):
    pass
