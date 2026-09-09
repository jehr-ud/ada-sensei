"""Textual-based interactive TUI (RQ-TUI-001..028).

The TUI only coordinates presentation and user interaction. Every slash command
is parsed into the same typed command objects and dispatched through the shared
:class:`CommandRouter` (RQ-TUI-003). Long-running operations run in workers so
the UI event loop is never blocked (RQ-TUI-016).
"""

from __future__ import annotations

import contextlib

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
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
    InternalFailure,
    PracticeCommand,
    QuitCommand,
    QuitResult,
)
from ..errors import CLIError
from ..formatter import Formatter
from ..parser import CommandParser
from ..router import CommandRouter
from .messages import OutputReady
from .state import PresentationState, View
from .widgets import PromptArea, SessionBar, SessionFooter

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

    def compose(self) -> ComposeResult:
        yield SessionBar(id="session-bar")
        yield RichLog(id="log", markup=True, wrap=True)
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
            status=self.ui_state.status,
        )

    def _status(self, text: str) -> None:
        self.ui_state.status = text
        self.refresh_footer()

    def _set_busy(self, busy: bool, status: str) -> None:
        self.ui_state.set_busy(busy, status)
        self._status(status)

    def _emit(self, text: str) -> None:
        if text:
            self.ui_state.push(text)
            with contextlib.suppress(Exception):
                self.post_message(OutputReady(text))

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
        self._handle_command(command)

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
            self._emit("Error: " + self.formatter.error(result.message))
        elif isinstance(result, QuitResult):
            self.exit()
        elif isinstance(result, ClearResult):
            with contextlib.suppress(Exception):
                self.query_one("#log", RichLog).clear()
            self.ui_state.messages.clear()
            self._set_busy(False, "Ready")
        else:
            self._set_busy(False, "Ready")
            text = self.formatter.result(result)
            self._emit(text if text else "(done)")
        notice = self.router.context_notice()
        if notice:
            self._emit("Note: " + self.formatter.error(notice))
        self.refresh_session_bar()
        self._focus_input()

    def on_output_ready(self, message: OutputReady) -> None:
        self.query_one("#log", RichLog).write(message.text)


if __name__ == "__main__":
    AdaSenseiTUI(router=CommandRouter()).run()
