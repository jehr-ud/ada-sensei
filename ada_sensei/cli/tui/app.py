"""Textual-based interactive TUI (RQ-TUI-001..028).

The TUI only coordinates presentation and user interaction. Every slash command
is parsed into the same typed command objects and dispatched through the shared
:class:`CommandRouter` (RQ-TUI-003). Long-running operations run in workers so
the UI event loop is never blocked (RQ-TUI-016).
"""

from __future__ import annotations

import contextlib
import re

from rich.syntax import Syntax
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.timer import Timer
from textual.widgets import Footer, Header, RichLog, Select
from textual.worker import Worker, WorkerState

from ...storage.history import HistoryStore
from ...storage.last_student import LastStudentStore
from ..commands import (
    AskCommand,
    ClearCommand,
    ClearResult,
    Command,
    CommandResult,
    ErrorResponse,
    EvaluateCommand,
    ExamplesCommand,
    HelpCommand,
    HintCommand,
    InternalFailure,
    MoreCommand,
    PracticeCommand,
    QuitCommand,
    QuitResult,
    SolutionCommand,
)
from ..errors import CLIError
from ..formatter import Formatter
from ..parser import CommandParser
from ..router import CommandRouter
from .messages import OutputReady
from .state import MessageKind, PresentationState, View
from .widgets import PromptArea, SessionBar, SessionFooter, StatusIndicator

HELP_TEXT = (
    "ADA Sensei commands\n\n"
    "Pick an action from the selector above (ask / practice / examples / evaluate)\n"
    "and type freely in the text field; press Enter to run that action.\n"
    "  e.g. action: ask, type: why does LazyColumn not update?, press Enter\n\n"
    "The text field is multi-line: Shift+Enter inserts a new line, Enter runs\n"
    "the selected action.\n"
    "Slash commands:\n"
    "  /help                      show this help\n"
    "  /practice, /ask, /examples, /evaluate   run an action\n"
    "  /hint, /more, /solution    advance the assistance level\n"
    "  /clear                     clear the view\n"
    "  /quit                      exit the TUI\n"
    "\n"
    "Examples:\n"
    "  /practice --topic compose-state --difficulty intermediate\n"
    "  /ask why does LazyColumn not update?\n"
    "  /examples ViewModel\n"
    "  /evaluate --yes\n"
    "  /hint\n"
    "\n"
    "Your name at startup is your student identity.\n"
    "  /name <name>             update your student identity\n"
)

#: Action selector options (label, value) — RQ-TUI-030.
ACTION_OPTIONS = [
    ("ask", "ask"),
    ("practice", "practice"),
    ("examples", "examples"),
    ("evaluate", "evaluate"),
]

#: Placeholder shown in the input depending on the selected action.
ACTION_PROMPTS = {
    "ask": "ask… e.g. why does LazyColumn not update?",
    "practice": "enter a topic… e.g. compose-state (optional)",
    "examples": "enter a topic… e.g. ViewModel",
    "evaluate": "evaluate the current project (Enter to run)",
}

#: Statuses that receive the animated ``Running…`` treatment.
ANIMATABLE_STATUSES = frozenset({"Running", "Evaluating"})

#: Dot-count cycle for the animation: ``Running``, ``Running.``, ``Running..``,
#: ``Running...``, then back down. The internal status stays machine-readable
#: ``Running``; only the *display* string animates (RQ-TUI-032/034).
ANIM_FRAMES = (0, 1, 2, 3, 2, 1)

#: Seconds between animation frames. Lightweight and event-loop driven; no busy
#: loop and no dedicated thread (RQ-TUI-016).
ANIM_INTERVAL = 0.4

#: Role label used in the conversation viewport per entry kind.
MESSAGE_LABELS = {
    MessageKind.USER: "You",
    MessageKind.ASSISTANT: "ADA Sensei",
    MessageKind.PRACTICE: "Practice",
    MessageKind.EXERCISE: "Exercise",
    MessageKind.HINT: "Hint",
    MessageKind.EXAMPLE: "Examples",
    MessageKind.EVALUATION: "Evaluation",
    MessageKind.ERROR: "Error",
}

#: Command type -> conversation role for result rendering (RQ-TUI-034).
_COMMAND_KINDS = {
    AskCommand: MessageKind.ASSISTANT,
    PracticeCommand: MessageKind.PRACTICE,
    ExamplesCommand: MessageKind.EXAMPLE,
    EvaluateCommand: MessageKind.EVALUATION,
    HintCommand: MessageKind.HINT,
    MoreCommand: MessageKind.HINT,
    SolutionCommand: MessageKind.HINT,
}

_FENCE_RE = re.compile(r"```")


class AdaSenseiTUI(App):
    """Main TUI application."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "quit", "Quit"),
        Binding("ctrl+c", "cancel_operation", "Cancel"),
        Binding("enter", "submit", "Enter Run"),
        Binding("f2", "show_help", "Help"),
    ]
    TITLE = "ADA Sensei"

    def __init__(
        self,
        router: CommandRouter,
        formatter: Formatter | None = None,
    ) -> None:
        super().__init__()
        self.router = router
        self.formatter = formatter or Formatter(router.secrets)
        self.ui_state = PresentationState()
        self._active_worker = None
        self._pending_eval: EvaluateCommand | None = None
        self._anim_timer: Timer | None = None
        self._anim_step = 0
        self._current_kind: MessageKind = MessageKind.SYSTEM

    def compose(self) -> ComposeResult:
        yield SessionBar(id="session-bar")
        yield RichLog(id="log", markup=True, wrap=True)
        yield StatusIndicator(id="status-indicator")
        with Horizontal(id="action-row"):
            yield Select(
                ACTION_OPTIONS,
                prompt="action",
                allow_blank=False,
                value="ask",
                id="action-select",
            )
        yield PromptArea("", id="input")
        yield SessionFooter(id="session-footer")
        yield Footer()
        yield Header()

    def on_mount(self) -> None:
        self.refresh_session_bar()
        self._focus_input()
        self.ui_state.awaiting_name = True
        self._set_name_prompt()
        remembered = self._remembered_name()
        if remembered:
            self._resolve_pending_name(remembered)
        else:
            self._emit("Welcome to ADA Sensei. What is your name?")

    def _focus_input(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#input", PromptArea).focus()

    def _remembered_name(self) -> str | None:
        store = LastStudentStore(str(self.router.config.resolved_data_dir))
        return store.load()

    def _set_name_prompt(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#input", PromptArea).placeholder = "your name… e.g. Ana"

    def _apply_action_prompt(self) -> None:
        with contextlib.suppress(Exception):
            placeholder = ACTION_PROMPTS.get(self.ui_state.action, "type a text…")
            self.query_one("#input", PromptArea).placeholder = placeholder

    def _set_identity(self, name: str) -> bool:
        """Bind ``name`` as the current identity and remember it.

        Returns whether the profile already existed (returning student).
        """
        self.ui_state.awaiting_name = False
        self.ui_state.user_name = name
        store = HistoryStore(str(self.router.config.resolved_data_dir))
        self.router.context.set_student(name)
        returning = store.has(name)
        if not returning:
            store.create_profile(name, confirmed=True)
        store.set_name(name, name)
        LastStudentStore(str(self.router.config.resolved_data_dir)).save(name)
        self.refresh_session_bar()
        return returning

    def _resolve_pending_name(self, raw: str) -> None:
        name = raw.strip()
        if not name:
            self.ui_state.awaiting_name = True
            self._emit("Sorry, I didn't catch that. What is your name?")
            return
        returning = self._set_identity(name)
        greeting = (
            f"Welcome back, {name}! Type /help for commands."
            if returning
            else f"Welcome, {name}! Type /help for commands."
        )
        self._emit(greeting)
        self._apply_action_prompt()

    def _handle_name_command(self, raw: str) -> None:
        name = raw.removeprefix("/name").strip()
        if not name:
            self._emit("Usage: /name <your name>")
            return
        self._set_identity(name)
        self._emit(f"Identity updated to {name}.")

    # ------------------------------------------------------------------
    # Presentation helpers
    # ------------------------------------------------------------------

    def refresh_session_bar(self) -> None:
        try:
            ctx = self.router.context
            bar = self.query_one("#session-bar", SessionBar)
        except Exception:
            return
        bar.refresh_context(ctx.student_id, ctx.project_id)
        self.refresh_footer()

    def refresh_footer(self) -> None:
        """Render the persistent session footer (RQ-TUI-032).

        Values come from authoritative sources only: the student identity from
        ``SessionContext`` (bound via the name the user provided), the score from
        the most recent evaluation result, the AI model from the configured LLM
        implementation, and the current action/status from presentation state.
        """
        try:
            footer = self.query_one("#session-footer", SessionFooter)
        except Exception:
            return
        footer.update_session(
            student=self.ui_state.user_name or self.router.context.student_id,
            score=self.router.last_score(),
            model=self.router.model_name(),
            action=self.ui_state.action,
            status=self._display_status(),
        )

    def _status(self, text: str) -> None:
        self.ui_state.status = text
        self.refresh_footer()

    def _set_busy(self, busy: bool, status: str) -> None:
        """Change the busy flag, restarting or stopping the status animation.

        The canonical, machine-readable status stays exactly ``status``
        (e.g. ``Running``); the visual animation is a presentation layer only
        (RQ-TUI-032/034/016).
        """
        self.ui_state.set_busy(busy, status)
        if busy and status in ANIMATABLE_STATUSES:
            self._start_animation()
        else:
            self._stop_animation()
        self._status(status)

    def _display_status(self) -> str:
        """Status shown to the user.

        Returns the animated form (``Running.``, ``Running..``, ...) while an
        animation is active, otherwise the canonical status string.
        """
        if (
            self._anim_timer is not None
            and self.ui_state.busy
            and self.ui_state.status in ANIMATABLE_STATUSES
        ):
            dots = ANIM_FRAMES[self._anim_step % len(ANIM_FRAMES)]
            return self.ui_state.status + ("." * dots)
        return self.ui_state.status

    def _start_animation(self) -> None:
        """Start the lightweight presentation animation (Textual interval).

        The timer only refreshes the footer status and the transient indicator;
        it never blocks the event loop or spawns a thread for animation. Before
        the app is mounted (or in constructed-only tests) no timer is created and
        the canonical status is shown without animation.
        """
        self._stop_animation()
        if self._is_mounted:
            with contextlib.suppress(Exception):
                self._anim_timer = self.set_interval(
                    ANIM_INTERVAL,
                    self._advance_animation,
                    name="status-animation",
                )
        self._anim_step = 0
        self._refresh_status_indicator(self._display_status())

    def _stop_animation(self) -> None:
        if self._anim_timer is not None:
            with contextlib.suppress(Exception):
                self._anim_timer.stop()
            self._anim_timer = None
        self._anim_step = 0
        self._refresh_status_indicator("")

    def _advance_animation(self) -> None:
        self._anim_step += 1
        self._refresh_status_indicator(self._display_status())
        self.refresh_footer()

    def _refresh_status_indicator(self, text: str) -> None:
        """Update (or hide) the transient in-conversation status message."""
        with contextlib.suppress(Exception):
            indicator = self.query_one("#status-indicator", StatusIndicator)
            if text:
                indicator.update(f"ADA Sensei  {text}")
                indicator.styles.display = "block"
            else:
                indicator.update("")
                indicator.styles.display = "none"

    def _emit(self, text: str) -> None:
        self._emit_kind(MessageKind.SYSTEM, text)

    def _emit_kind(self, kind: MessageKind | str, text: str) -> None:
        if text:
            self.ui_state.push(text)
            with contextlib.suppress(Exception):
                self.post_message(OutputReady(text, kind=MessageKind(kind)))

    def _emit_user(self, text: str) -> None:
        """Render the submitted line as a distinct user message (RQ-TUI-034)."""
        self._emit_kind(MessageKind.USER, text)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def action_show_help(self) -> None:
        self.ui_state.view = View.HELP
        self._emit(HELP_TEXT)
        self._focus_input()

    def action_cancel_operation(self) -> None:
        self.ui_state.cancelled = True
        if self._active_worker is not None and not self._active_worker.is_cancelled:
            self._active_worker.cancel()
        self._set_busy(False, "Cancelled")
        self._focus_input()

    @on(Select.Changed, "#action-select")
    def on_action_select_changed(self, event: Select.Changed) -> None:
        self.ui_state.action = str(event.value)
        self._apply_action_prompt()
        self.refresh_footer()
        self._focus_input()

    def action_submit(self) -> None:
        area = self.query_one("#input", PromptArea)
        line = (area.text or "").strip()
        if area.text:
            area.clear()
        self._process_line(line)
        self._focus_input()

    @on(PromptArea.PromptSubmitted)
    def on_prompt_submitted(self, message: PromptArea.PromptSubmitted) -> None:
        self.action_submit()

    def _process_line(self, line: str) -> None:
        if not line:
            if self.ui_state.awaiting_name:
                self._resolve_pending_name("")
                return
            # Empty free text is only meaningful for an empty practice topic
            # (RQ-TUI-030) or for running the evaluate flow.
            if self.ui_state.action not in ("practice", "evaluate"):
                return
        if self.ui_state.awaiting_name:
            self._resolve_pending_name(line)
            return
        if self._pending_eval is not None:
            self._resolve_pending_eval(self._pending_eval, line)
            return
        if line.startswith("/name"):
            self._handle_name_command(line)
            return
        try:
            command = self._command_from_line(line)
        except Exception as exc:
            self._emit("Error: " + self.formatter.error(str(exc)))
            return
        self._render_user_message(line, command)
        self._handle_command(command)

    def _render_user_message(self, line: str, command: Command) -> None:
        """Show the submitted request as a distinct user message for actions."""
        if not isinstance(command, (AskCommand, PracticeCommand, ExamplesCommand, EvaluateCommand)):
            return
        shown = line if line else "(evaluate the current project)"
        self._emit_user(shown)

    def _command_from_line(self, line: str) -> Command:
        """Build a command from submitted text (RQ-TUI-030).

        Slash-prefixed input is parsed as a slash command; anything else is
        sent to the currently selected action from the action selector.
        """
        if line.startswith("/"):
            return CommandParser.parse_line(line)
        action = self.ui_state.action
        if action == "ask":
            return AskCommand(question=line)
        if action == "practice":
            return PracticeCommand(topic=line or None)
        if action == "examples":
            return ExamplesCommand(topic=line)
        if action == "evaluate":
            return EvaluateCommand()
        raise CLIError(f"no text action selected: {action!r}")

    def _handle_command(self, command: Command) -> None:
        if isinstance(command, QuitCommand):
            self.exit()
            return
        if isinstance(command, HelpCommand):
            self.action_show_help()
            return
        if isinstance(command, ClearCommand):
            with contextlib.suppress(Exception):
                self.query_one("#log", RichLog).clear()
            self.ui_state.messages.clear()
            self._emit("(view cleared)")
            return
        if isinstance(command, EvaluateCommand):
            self._confirm_then_run(command)
            return
        self._run_nonblocking(command)

    # ------------------------------------------------------------------
    # Evaluation with confirmation (RQ-TUI-013 / 014)
    # ------------------------------------------------------------------

    def _confirm_then_run(self, command: EvaluateCommand) -> None:
        if command.confirmed:
            self._run_nonblocking(command)
            return
        self.ui_state.view = View.EVALUATE
        self._pending_eval = command
        self._status("Waiting for confirmation")
        self._emit(
            "Evaluation runs Gradle build/tests/lint/detekt. "
            "Reply `yes` to confirm or `no` to abort."
        )

    def _resolve_pending_eval(self, pending: EvaluateCommand, answer: str) -> None:
        self._pending_eval = None
        self.ui_state.view = View.CHAT
        if answer.strip().lower() in {"y", "yes"}:
            self._run_nonblocking(pending)
        else:
            self._status("Ready")
            self._emit("Evaluation aborted before running any Gradle task.")
            self._focus_input()

    # ------------------------------------------------------------------
    # Non-blocking dispatch (RQ-TUI-016 / 017)
    # ------------------------------------------------------------------

    def _run_nonblocking(self, command: Command) -> None:
        status = "Evaluating" if isinstance(command, EvaluateCommand) else "Running"
        self._current_kind = _COMMAND_KINDS.get(type(command), MessageKind.SYSTEM)
        self._set_busy(True, status)
        worker = self.run_worker(
            lambda: self._dispatch_worker(command),
            thread=True,
            exclusive=True,
            exit_on_error=False,
        )
        self._active_worker = worker

    @on(Worker.StateChanged)
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._active_worker:
            return
        if event.state not in (
            WorkerState.SUCCESS,
            WorkerState.ERROR,
            WorkerState.CANCELLED,
        ):
            return
        self._active_worker = None
        self._on_worker_done(event.worker)

    def _dispatch_worker(self, command: Command) -> CommandResult:
        return self.router.dispatch(command)

    def _on_worker_done(self, worker: Worker) -> None:
        error = worker.error
        if error is not None:
            self._set_busy(False, "Error")
            self._emit("Error: " + self.formatter.sanitized(error))
            self.refresh_session_bar()
            self._focus_input()
            return
        result = worker.result
        if isinstance(result, (ErrorResponse, InternalFailure)):
            self._set_busy(False, "Error")
            self._emit_kind(
                MessageKind.ERROR, "Error: " + self.formatter.error(result.message)
            )
        elif isinstance(result, QuitResult):
            self.exit()
        elif isinstance(result, ClearResult):
            with contextlib.suppress(Exception):
                self.query_one("#log", RichLog).clear()
            self.ui_state.messages.clear()
            self._set_busy(False, "Ready")
        else:
            kind = self._current_kind
            self._set_busy(False, "Ready")
            text = self.formatter.result(result)
            self._emit_kind(kind, text if text else "(done)")
        notice = self.router.context_notice()
        if notice:
            self._emit("Note: " + self.formatter.error(notice))
        self.refresh_session_bar()
        self._focus_input()

    def on_output_ready(self, message: OutputReady) -> None:
        self._write_output(message.kind, message.text)

    # ------------------------------------------------------------------
    # Conversation rendering (RQ-TUI-034)
    # ------------------------------------------------------------------

    def _write_output(self, kind: MessageKind, text: str) -> None:
        """Append a distinguished conversation entry to the log.

        User/assistant/result entries get a role label, a divider, and wrapped
        body content; code blocks are preserved and rendered with Rich Syntax.
        System entries keep the previous plain rendering.
        """
        if not text:
            return
        try:
            log = self.query_one("#log", RichLog)
        except Exception:
            # A pending entry may be delivered around unmount (e.g. at app
            # shutdown); there is nowhere meaningful to render it then.
            return
        if kind is MessageKind.SYSTEM:
            log.write(text)
            return
        label = MESSAGE_LABELS.get(kind)
        width = max((log.size.width or 60), 12)
        if label:
            log.write(Text(f"  {label}\n", style="bold"))
            log.write(Text("  " + "─" * max(width - 2, 1) + "\n", style="dim"))
        self._write_body(log, text)

    @staticmethod
    def _write_body(log: RichLog, text: str) -> None:
        """Write body content, rendering fenced code blocks via Rich Syntax.

        Prose paragraphs wrap at the terminal width (RichLog ``wrap=True``);
        code preserves its formatting and becomes horizontally/vertically
        scrollable instead of being truncated.
        """
        # Splitting on the fence token yields alternating plain/code parts.
        # Inside a code part the first line is the language annotation.
        parts = _FENCE_RE.split(text)
        for index, part in enumerate(parts):
            if index % 2 == 0:
                # Plain prose: escape any rich markup by using literal Text so
                # user content is never misinterpreted or truncated.
                for chunk in part.split("\n\n"):
                    chunk = chunk.strip("\n")
                    if chunk:
                        log.write(Text(chunk))
            else:
                lines = part.splitlines()
                lang = lines[0].strip() or "text" if lines else "text"
                code = "\n".join(lines[1:]) if len(lines) > 1 else ""
                if not code:
                    continue
                try:
                    log.write(Syntax(code, lang, theme="ansi_dark", word_wrap=False))
                except Exception:
                    log.write(Text(code))


if __name__ == "__main__":
    AdaSenseiTUI(router=CommandRouter()).run()
