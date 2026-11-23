"""Textual-based interactive TUI (RQ-TUI-001..028).

The TUI only coordinates presentation and user interaction. Every slash command
is parsed into the same typed command objects and dispatched through the shared
:class:`CommandRouter` (RQ-TUI-003). Long-running operations run in workers so
the UI event loop is never blocked (RQ-TUI-016).
"""

from __future__ import annotations

import contextlib
import re
from pathlib import Path

from rich.syntax import Syntax
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.timer import Timer
from textual.widgets import Button, Footer, Header, RichLog, Select
from textual.worker import Worker, WorkerState

from ...actions.examine import ExamFinishResult
from ...locale.ui_strings import describe_blocker, get_ui_string
from ...storage.history import HistoryStore
from ...storage.last_student import LastStudentStore
from ...tools.opener import open_path
from ..action_registry import get_actions as _registry_actions
from ..commands import (
    AskCommand,
    ClearCommand,
    ClearResult,
    Command,
    CommandResult,
    DiagnoseCommand,
    ErrorResponse,
    EvaluateCommand,
    ExamineFinishCommand,
    ExamineStartCommand,
    ExamplesCommand,
    HelpCommand,
    HintCommand,
    InternalFailure,
    LanguageCommand,
    LearnCommand,
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
from .history import InputHistory
from .messages import OutputReady
from .state import MessageKind, PresentationState, View
from .widgets import (
    ActionGuide,
    ActionSelector,
    ExamPreparationList,
    LanguageList,
    PromptArea,
    SessionBar,
    SessionFooter,
    StatusIndicator,
)

HELP_TEXT = (
    "ADA Sensei commands\n\n"
    "Pick an action from the selector above "
    "(ask / practice / examples / evaluate / exam-init / exam-finish / "
    "learn / diagnose / language / help)\n"
    "and type freely in the text field; press Enter to run that action.\n"
    "  e.g. action: ask, type: why does LazyColumn not update?, press Enter\n\n"
    "The text field is multi-line: Shift+Enter inserts a new line, Enter runs\n"
    "the selected action.\n"
    "Slash commands:\n"
    "  /help                      show this help\n"
    "  /practice, /ask, /examples, /evaluate   run an action\n"
    "  /exam-init <statement>      start an exam (asks for confirmation)\n"
    "  /exam-finish               finish the active exam (asks for confirmation)\n"
    "  /project <path>             configure the Android project for an exam\n"
    "  /instructions <path.md>     configure the teacher's exam statement\n"
    "  /learn [topic]              explain current-stage concepts\n"
    "  /diagnose [stage]           run a brief diagnostic\n"
    "  /language <locale>          change language (es-CO | en-US)\n"
    "  /hint, /more, /solution    advance the assistance level\n"
    "  /clear                     clear the view\n"
    "  /quit                      exit the TUI\n"
    "\n"
    "Examples:\n"
    "  /practice --topic compose-state --difficulty intermediate\n"
    "  /ask why does LazyColumn not update?\n"
    "  /examples ViewModel\n"
    "  /evaluate --yes\n"
    "  /exam-init docs/exam.md\n"
    "  /exam-finish\n"
    "  /hint\n"
    "\n"
    "Your name at startup is your student identity.\n"
    "  /name <name>             update your student identity\n"
)

#: Action selector options (label, value) — RQ-TUI-030/032/035.
#: Derived from the centralized registry (``cli/action_registry.py``); the
#: module-level default uses stable ids so headless tests and the CLI keep
#: working, while the running app refreshes labels per locale via
#: :func:`localized_action_options`.
ACTION_OPTIONS = [
    ("ask", "ask"),
    ("practice", "practice"),
    ("examples", "examples"),
    ("evaluate", "evaluate"),
    ("exam-init", "exam-init"),
    ("exam-finish", "exam-finish"),
    ("learn", "learn"),
    ("diagnose", "diagnose"),
    ("language", "language"),
    ("help", "help"),
]

#: Placeholder shown in the input depending on the selected action.
#: English defaults; :func:`action_prompt` resolves the localized hint.
ACTION_PROMPTS = {
    "ask": "ask… e.g. why does LazyColumn not update?",
    "practice": "enter a topic… e.g. compose-state (optional)",
    "examples": "enter a topic… e.g. ViewModel",
    "evaluate": "evaluate the current project (Enter to run)",
    "exam-init": "exam statement… e.g. docs/exam.md (Enter to start)",
    "exam-finish": "finish the exam and generate the report (Enter to run)",
    "learn": "topic… e.g. Compose state (optional)",
    "diagnose": "stage… e.g. kotlin-fundamentals (optional)",
    "language": "locale… es-CO or en-US",
    "help": "show help (Enter to view)",
}


def localized_action_options(locale: str | None) -> list[tuple[str, str]]:
    """Localized ``(label, value)`` selector options for ``locale``.

    Values (stable action ids) are never translated; only labels follow the
    selected locale (RQ-LNG-005/007).
    """
    options: list[tuple[str, str]] = []
    for action in _registry_actions():
        options.append((action.label(locale), action.id))
    return options


def action_prompt(action_id: str, locale: str | None) -> str:
    """Localized input hint for ``action_id`` with English fallback."""
    for action in _registry_actions():
        if action.id == action_id:
            return action.hint(locale)
    return ACTION_PROMPTS.get(action_id, "type a text…")


#: Commands that require an explicit confirmation before running.
CONFIRMING_ACTIONS = ("evaluate", "exam-init", "exam-finish")

#: Statuses that receive the animated ``Running…`` treatment.
ANIMATABLE_STATUSES = frozenset({"Running", "Evaluating", "Examining"})

#: Dot-count cycle for the animation: ``Running``, ``Running.``, ``Running..``,
#: ``Running...``, then back down. The internal status stays machine-readable
#: ``Running``; only the *display* string animates (RQ-TUI-032/034).
ANIM_FRAMES = (0, 1, 2, 3, 2, 1)

#: Seconds between animation frames. Lightweight and event-loop driven; no busy
#: loop and no dedicated thread (RQ-TUI-016).
ANIM_INTERVAL = 0.4

#: Seconds between exam-timer footer refreshes while an exam is active.
EXAM_TIMER_INTERVAL = 1.0

#: Role label used in the conversation viewport per entry kind.
MESSAGE_LABELS = {
    MessageKind.USER: "You",
    MessageKind.ASSISTANT: "ADA Sensei",
    MessageKind.PRACTICE: "Practice",
    MessageKind.EXERCISE: "Exercise",
    MessageKind.HINT: "Hint",
    MessageKind.EXAMPLE: "Examples",
    MessageKind.EVALUATION: "Evaluation",
    MessageKind.EXAM: "Exam",
    MessageKind.ERROR: "Error",
}

#: Command type -> conversation role for result rendering (RQ-TUI-034).
_COMMAND_KINDS = {
    AskCommand: MessageKind.ASSISTANT,
    PracticeCommand: MessageKind.PRACTICE,
    ExamplesCommand: MessageKind.EXAMPLE,
    EvaluateCommand: MessageKind.EVALUATION,
    ExamineStartCommand: MessageKind.EXAM,
    ExamineFinishCommand: MessageKind.EXAM,
    LearnCommand: MessageKind.ASSISTANT,
    DiagnoseCommand: MessageKind.ASSISTANT,
    LanguageCommand: MessageKind.SYSTEM,
    HelpCommand: MessageKind.SYSTEM,
    HintCommand: MessageKind.HINT,
    MoreCommand: MessageKind.HINT,
    SolutionCommand: MessageKind.HINT,
}

#: Commands whose result is shown as a distinct user request in the log.
_USER_VISIBLE_COMMANDS = (
    AskCommand,
    PracticeCommand,
    ExamplesCommand,
    EvaluateCommand,
    ExamineStartCommand,
    ExamineFinishCommand,
    LearnCommand,
    DiagnoseCommand,
    LanguageCommand,
)

#: Command type -> stable registry action id (spec 0011 §5: recommendations
#: use stable ids, never localized labels as executable values).
_COMMAND_ACTION_IDS = {
    AskCommand: "ask",
    PracticeCommand: "practice",
    ExamplesCommand: "examples",
    EvaluateCommand: "evaluate",
    ExamineStartCommand: "exam-init",
    ExamineFinishCommand: "exam-finish",
    LearnCommand: "learn",
    DiagnoseCommand: "diagnose",
    LanguageCommand: "language",
    HelpCommand: "help",
}

#: Commands that run the Gradle evidence scope.
_EVIDENCE_COMMANDS = (EvaluateCommand, ExamineFinishCommand)

#: Confirmation prompt shown before a consequential action runs.
_CONFIRM_PROMPT = {
    EvaluateCommand: (
        "Evaluation runs Gradle build/tests/lint/detekt. "
        "Reply `yes` to confirm or `no` to abort."
    ),
    ExamineStartCommand: (
        "Starting an exam records its duration and every /ask, and writes "
        "documentation into the project under docs/ada-sensei/. "
        "Reply `yes` to start the exam or `no` to abort."
    ),
    ExamineFinishCommand: (
        "Finishing the exam stops the timer, scores the project, and writes a "
        "PDF report. Reply `yes` to confirm or `no` to abort."
    ),
}

#: Localized confirmation guidance key per command.
_CONFIRM_STRING_KEYS = {
    EvaluateCommand: "evaluate_confirm",
    ExamineStartCommand: "exam_start_confirm",
    ExamineFinishCommand: "exam_finish_confirm",
}

#: Confirmation aborted message per command.
_ABORT_ECHO = {
    EvaluateCommand: "Evaluation aborted before running any Gradle task.",
    ExamineStartCommand: "Exam start aborted; no attempt was created.",
    ExamineFinishCommand: "Exam finish aborted; the attempt is still active.",
}

#: Localized abort message key per command.
_ABORT_STRING_KEYS = {
    EvaluateCommand: "evaluate_aborted",
    ExamineStartCommand: "exam_start_aborted",
    ExamineFinishCommand: "exam_finish_aborted",
}

#: Echo used as the user message when a no-argument action is submitted empty.
_PLACEHOLDER_ECHO = {
    EvaluateCommand: "evaluate the current project",
    ExamineFinishCommand: "finish the exam",
    LearnCommand: "learn the current stage",
    DiagnoseCommand: "run a diagnostic",
    LanguageCommand: "change language",
}

#: Presentation view shown while waiting for each confirmation.
_CONFIRM_VIEW = {
    EvaluateCommand: View.EVALUATE,
    ExamineStartCommand: View.EXAM_START,
    ExamineFinishCommand: View.EXAM_FINISH,
}

#: Status shown while a command runs, keyed by the scope it touches.
_RUN_STATUS = {
    EvaluateCommand: "Evaluating",
    ExamineFinishCommand: "Examining",
    ExamineStartCommand: "Examining",
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
        #: Session-local submitted-prompt history (RQ-TUI-039). Owned by the
        #: App and shared with the input widget; never persisted to disk.
        self.input_history = InputHistory()
        self._active_worker = None
        self._pending_eval: EvaluateCommand | None = None
        self._pending_exam: (
            EvaluateCommand | ExamineStartCommand | ExamineFinishCommand | None
        ) = None
        self._exam_preparing = False
        #: Last blocker set emitted for the preparation panel (dedup guard).
        self._exam_prep_signature: tuple[str, ...] | None = None
        #: Start exam guidance was already emitted when the action was picked.
        self._exam_start_offer_shown: bool = False
        self._anim_timer: Timer | None = None
        self._anim_step = 0
        self._current_kind: MessageKind = MessageKind.SYSTEM
        self._exam_timer: Timer | None = None
        #: Explicit language-selection flow active (spec 0010).
        self._pending_language: bool = False
        #: Cursor state of the open language list; ``None`` when closed.
        self._language_selection = None
        #: Whether the open list is the first-run gate before onboarding.
        self._language_first_run: bool = False
        #: Continue to onboarding once the first-run locale persists.
        self._resume_onboarding: bool = False
        #: First-run onboarding flow active (spec 008, RQ-LRN-004).
        self._pending_onboarding: bool = False
        #: Stable registry action id of the last dispatched command, used for
        #: context-aware recommendations (spec 0011 §5).
        self._last_action_id: str | None = None

    def compose(self) -> ComposeResult:
        yield SessionBar(id="session-bar")
        yield RichLog(id="log", markup=True, wrap=True)
        yield StatusIndicator(id="status-indicator")
        with Horizontal(id="action-row"):
            yield ActionSelector(
                ACTION_OPTIONS,
                prompt="action",
                allow_blank=False,
                value="ask",
                id="action-select",
            )
        with Horizontal(id="confirm-bar"):
            yield Button("Confirm", id="confirm-yes", variant="success")
            yield Button("Cancel", id="confirm-no", variant="error")
        yield ActionGuide(id="action-guide")
        yield LanguageList(id="language-list")
        yield ExamPreparationList(id="exam-preparation-list")
        yield PromptArea("", id="input")
        yield SessionFooter(id="session-footer")
        yield Footer()
        yield Header()

    def on_mount(self) -> None:
        self._refresh_selector_labels()
        self._refresh_guide()
        self.refresh_session_bar()
        with contextlib.suppress(Exception):
            self.query_one("#input", PromptArea).input_history = self.input_history
        self._focus_input()
        self.ui_state.awaiting_name = True
        self._set_name_prompt()
        remembered = self._remembered_name()
        if remembered:
            self._resolve_pending_name(remembered)
        else:
            self._emit("Welcome to ADA Sensei. What is your name?")

    # ------------------------------------------------------------------
    # Exam timer (RQ-EXM-007)
    # ------------------------------------------------------------------

    def _sync_exam_timer(self) -> None:
        """Run the footer refresh only while an exam is in progress.

        Presentation only: the elapsed value comes from the persisted attempt,
        so a paused or throttled UI can never change the recorded duration.
        """
        status = self._exam_status()
        active = status is not None and status.is_active
        if active and self._exam_timer is None and self._is_mounted:
            with contextlib.suppress(Exception):
                self._exam_timer = self.set_interval(
                    EXAM_TIMER_INTERVAL,
                    self.refresh_footer,
                    name="exam-timer",
                )
        elif not active and self._exam_timer is not None:
            with contextlib.suppress(Exception):
                self._exam_timer.stop()
            self._exam_timer = None
        self.refresh_footer()

    def _focus_input(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#input", PromptArea).focus()

    def _remembered_name(self) -> str | None:
        store = LastStudentStore(str(self.router.config.resolved_data_dir))
        return store.load()

    def _set_name_prompt(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#input", PromptArea).placeholder = "your name… e.g. Ana"

    def _current_locale(self) -> str:
        getter = getattr(self.router, "current_locale", None)
        if callable(getter):
            with contextlib.suppress(Exception):
                found = getter()
                if found:
                    return str(found)
        return "en-US"

    def _refresh_selector_labels(self) -> None:
        """Refresh selector labels for the active locale (RQ-LNG-005).

        Values (stable action ids) are unchanged; only visible labels follow
        the locale. Progress and attempts are never touched here.
        """
        with contextlib.suppress(Exception):
            select = self.query_one("#action-select", Select)
            locale = self._current_locale()
            select.set_options(localized_action_options(locale))
        self._refresh_guide()

    def _refresh_guide(self) -> None:
        """Show guidance for the focused action (spec 0011 §3).

        Localized description + expected input + outcome + activation hint,
        sourced from the registry via the router. Never blank: falls back to
        the activation hint when the action is unknown.
        """
        with contextlib.suppress(Exception):
            guide = self.query_one("#action-guide", ActionGuide)
            describe = getattr(self.router, "describe_action", None)
            if callable(describe):
                text = describe(self.ui_state.action)
            else:
                from ..action_registry import action_guidance

                text = action_guidance(self.ui_state.action, self._current_locale())
            guide.update(text)

    def _apply_action_prompt(self) -> None:
        with contextlib.suppress(Exception):
            placeholder = action_prompt(self.ui_state.action, self._current_locale())
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
        self._maybe_start_onboarding()

    def _handle_name_command(self, raw: str) -> None:
        name = raw.removeprefix("/name").strip()
        if not name:
            self._emit("Usage: /name <your name>")
            return
        self._set_identity(name)
        self._emit(f"Identity updated to {name}.")

    # ------------------------------------------------------------------
    # First-run onboarding from the validated catalog (spec 008, RQ-LRN-004/005)
    # ------------------------------------------------------------------

    def _onboarding_services(self):
        """Return (profile_store, catalog, locale) or ``None`` on config error."""
        from ...learning.catalog import ConfigLoadError, LearningCatalogLoader
        from ...learning.stores import LearningProfileStore
        from ...locale.ui_strings import get_ui_string

        locale = self._current_locale()
        try:
            catalog = LearningCatalogLoader().load_catalog(locale)
        except ConfigLoadError as exc:
            self._emit(get_ui_string("onboard_config_error", locale).format(detail=exc))
            return None
        store = LearningProfileStore(str(self.router.config.resolved_data_dir))
        return store, catalog, locale

    def _maybe_start_onboarding(self) -> None:
        """Show dynamic onboarding when the student has no learning profile.

        Spec 0010 (RQ-LNG-002): when no language preference exists yet, the
        language list comes first and onboarding resumes after confirmation.
        """
        if self._pending_onboarding or self.ui_state.awaiting_name:
            return
        student_id = self.router.context.student_id
        if not student_id:
            return
        saved = None
        getter = getattr(self.router, "saved_locale", None)
        if callable(getter):
            with contextlib.suppress(Exception):
                saved = getter()
        if saved is None and not self._pending_language:
            self._start_language_flow(first_run=True)
            return
        from ...learning.stores import LearningProfileStore

        try:
            has_profile = (
                LearningProfileStore(str(self.router.config.resolved_data_dir)).get(
                    student_id
                )
                is not None
            )
        except Exception:  # noqa: BLE001 - degraded storage skips onboarding
            return
        if has_profile:
            return
        services = self._onboarding_services()
        if services is None:
            return
        _, catalog, locale = services
        from ...learning.onboarding import (
            get_onboarding_content,
            render_onboarding,
        )

        self._pending_onboarding = True
        self._emit(render_onboarding(get_onboarding_content(catalog, locale)))
        self._focus_input()

    def _resolve_pending_onboarding(self, raw: str) -> None:
        """Resolve one onboarding reply: diagnose, skip, or a stage choice."""
        from ...learning.onboarding import (
            OnboardingError,
            choose_starting_stage,
            get_onboarding_content,
            interpret_choice,
            render_onboarding,
            start_with_default,
            start_with_diagnostic,
        )
        from ...locale.ui_strings import get_ui_string

        services = self._onboarding_services()
        if services is None:
            return
        store, catalog, locale = services
        student_id = self.router.context.student_id or ""
        kind, payload = interpret_choice(raw)
        unmet: list[str] = []
        try:
            if kind == "diagnose":
                profile = start_with_diagnostic(
                    store, catalog, student_id=student_id, locale=locale
                )
            elif kind == "skip":
                profile = start_with_default(
                    store, catalog, student_id=student_id, locale=locale
                )
            else:
                profile, unmet = choose_starting_stage(
                    store,
                    catalog,
                    student_id=student_id,
                    locale=locale,
                    selection=payload,
                )
        except OnboardingError:
            self._emit(get_ui_string("onboard_unknown", locale))
            self._emit(render_onboarding(get_onboarding_content(catalog, locale)))
            self._focus_input()
            return
        self._pending_onboarding = False
        if kind == "diagnose":
            self._emit(
                get_ui_string("onboard_diagnostic", locale).format(
                    title=self._stage_title(catalog, profile.current_stage_id)
                )
            )
        else:
            stage = next(s for s in catalog.stages if s.id == profile.current_stage_id)
            self._emit(
                get_ui_string("onboard_started", locale).format(
                    number=stage.number, title=stage.title
                )
            )
            if kind == "stage" and unmet:
                self._emit(
                    get_ui_string("onboard_prereqs", locale).format(
                        stage=profile.current_stage_id,
                        prereqs=", ".join(unmet),
                    )
                )
        self.refresh_session_bar()
        if kind == "diagnose":
            self._handle_command(DiagnoseCommand(stage_id=None))
        self._focus_input()

    @staticmethod
    def _stage_title(catalog, stage_id: str) -> str:
        for stage in catalog.stages:
            if stage.id == stage_id:
                return stage.title
        return stage_id

    # ------------------------------------------------------------------
    # Presentation helpers
    # ------------------------------------------------------------------

    def refresh_session_bar(self) -> None:
        try:
            ctx = self.router.context
            bar = self.query_one("#session-bar", SessionBar)
        except Exception:
            return
        version = None
        stage_text = None
        with contextlib.suppress(Exception):
            version = self.router.app_version()
        with contextlib.suppress(Exception):
            status = self.router.learning_stage()
            stage_text = status.display(self._current_locale())
        bar.refresh_context(
            ctx.student_id, ctx.project_id, version=version, stage_text=stage_text
        )
        self.refresh_footer()

    def refresh_footer(self) -> None:
        """Render the persistent session footer (RQ-TUI-032/035/036).

        Values come from authoritative sources only: the student identity from
        ``SessionContext`` (bound via the name the user provided), the score from
        the most recent evaluation result, the AI model from the configured LLM
        implementation, the learning stage from persisted progress + catalog,
        the app version from build metadata, and the current action/status from
        presentation state.
        """
        try:
            footer = self.query_one("#session-footer", SessionFooter)
        except Exception:
            return
        stage_text = None
        version = None
        locale = self._current_locale()
        with contextlib.suppress(Exception):
            stage_text = self.router.learning_stage().display(locale)
        with contextlib.suppress(Exception):
            version = self.router.app_version()
        footer.update_session(
            student=self.ui_state.user_name or self.router.context.student_id,
            score=self.router.last_score(),
            model=self.router.model_name(),
            action=self.ui_state.action,
            status=self._display_status(),
            exam=self._exam_status(),
            stage=stage_text,
            version=version,
            locale=locale,
        )

    def _exam_status(self):
        """Authoritative exam status, or ``None`` when no exam is active.

        Read through the router so the TUI renders persisted state only; it
        never counts asks or measures the exam itself (RQ-EXM-031).
        """
        getter = getattr(self.router, "exam_status", None)
        if getter is None:
            return None
        return getter()

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
        self._refresh_guide()
        self.refresh_footer()
        action = str(event.value)
        if action != "exam-init":
            # Changing actions abandons any confirmation that was still open.
            self._exam_start_offer_shown = False
            self._pending_exam = None
            self._pending_eval = None
            self._set_confirmation_visible(False)
            self._close_exam_preparation()
        if action == "exam-init":
            self._open_exam_preparation()
            self._show_exam_start_offer()
            return
        if action == "exam-finish":
            # Selecting the finish action must immediately expose its explicit
            # compact confirmation; the input intentionally remains blank.
            self._open_finish_confirmation()
            return
        if action == "language" and self._language_selection is None:
            # RQ-LNG-015: picking Change language opens the shared list
            # immediately — no extra Enter needed. The list takes focus.
            self._start_language_flow()
            return
        self._focus_input()

    @on(ActionSelector.LanguageRequested)
    def on_selector_language_requested(
        self, message: ActionSelector.LanguageRequested
    ) -> None:
        """Open the language list from the selector itself (RQ-LNG-015).

        Enter while the selector is focused used to only toggle the dropdown,
        so the list never opened from here. The widget already matched the
        stable `language` id; reuse the exact welcome/selector flow. No free
        text is built or dispatched to TeacherAgent on this path.
        """
        if self._language_selection is not None:
            with contextlib.suppress(Exception):
                self.query_one("#language-list", LanguageList).focus()
            return
        self._start_language_flow()

    def action_submit(self) -> None:
        # While the language list is open, Enter confirms the focused
        # language instead of dispatching prompt text (RQ-LNG-005).
        if self._language_selection is not None:
            self._confirm_focused_language()
            return
        area = self.query_one("#input", PromptArea)
        line = (area.text or "").strip()
        if area.text:
            area.clear()
        # Record every non-empty submission for Up/Down recall (RQ-TUI-039).
        # Blank lines are ignored; assistant/system output is never recorded
        # because only submitted input passes through here.
        self.input_history.record(line)
        self._process_line(line)
        self._focus_input()

    @on(PromptArea.PromptSubmitted)
    def on_prompt_submitted(self, message: PromptArea.PromptSubmitted) -> None:
        self.action_submit()

    def _process_line(self, line: str) -> None:
        # While the language list is open, free text is ignored (the list
        # owns the keyboard); slash commands still pass through.
        if self._language_selection is not None and not line.startswith("/"):
            return
        if not line:
            if self.ui_state.awaiting_name:
                self._resolve_pending_name("")
                return
            # Empty free text is only meaningful for actions that accept an
            # empty input (RQ-TUI-030) or for running a no-argument action.
            # Actions requiring text never leave a blank unexplained prompt:
            # they explain what the student must provide (spec 0011 REQ-003).
            if self.ui_state.action not in (
                "practice",
                "evaluate",
                "exam-finish",
                "learn",
                "diagnose",
                "language",
                "help",
            ):
                from ...locale.ui_strings import get_ui_string as _ui

                _prompts = {
                    "ask": "prereq_question",
                    "examples": "prereq_topic",
                    "exam-init": "prereq_statement",
                }
                _key = _prompts.get(self.ui_state.action)
                if _key is not None:
                    self._emit(_ui(_key, self._current_locale()))
                return
        if self.ui_state.awaiting_name:
            self._resolve_pending_name(line)
            return
        if self._pending_exam is not None:
            self._resolve_pending_exam(self._pending_exam, line)
            return
        if self._pending_onboarding and not line.startswith("/"):
            self._resolve_pending_onboarding(line)
            return
        if line.startswith("/name"):
            self._handle_name_command(line)
            self._maybe_start_onboarding()
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
        if not isinstance(command, _USER_VISIBLE_COMMANDS):
            return
        echo = _PLACEHOLDER_ECHO.get(type(command), type(command).__name__)
        shown = line or f"({echo})"
        self._emit_user(shown)

    def _command_from_line(self, line: str) -> Command:
        """Build a command from submitted text (RQ-TUI-030/032).

        Slash-prefixed input is parsed as a slash command; anything else is
        sent to the currently selected action from the action selector via the
        shared registry, producing the same typed commands as the CLI.
        """
        if line.startswith("/"):
            return CommandParser.parse_line(line)
        action = self.ui_state.action
        if action == "ask":
            return AskCommand(
                question=line,
                # Read at emit time, not here: the worker starts after this
                # command is built, and ``_run_nonblocking`` clears the flag
                # first. A run the student aborts is then recorded as cancelled
                # instead of completed, so it is not charged to the exam ask
                # allowance (RQ-EXM-005).
                is_cancelled=lambda: self.ui_state.cancelled,
            )
        if action == "practice":
            return PracticeCommand(topic=line or None)
        if action == "examples":
            return ExamplesCommand(topic=line)
        if action == "evaluate":
            return EvaluateCommand()
        if action == "exam-init":
            return ExamineStartCommand(statement=line)
        if action == "exam-finish":
            return ExamineFinishCommand()
        if action == "learn":
            return LearnCommand(topic=line or None)
        if action == "diagnose":
            return DiagnoseCommand(stage_id=line or None)
        if action == "language":
            return LanguageCommand(locale=line or None)
        if action == "help":
            return HelpCommand(scope=None)
        raise CLIError(f"no text action selected: {action!r}")

    def _handle_command(self, command: Command) -> None:
        # Prevent duplicate submissions while an action is running (the worker
        # is exclusive); cancellation remains available via Ctrl+C.
        if self.ui_state.busy and not isinstance(
            command, (QuitCommand, HelpCommand, ClearCommand)
        ):
            from ...locale.ui_strings import get_ui_string

            self._emit(get_ui_string("busy_blocked", self._current_locale()))
            return
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
        if isinstance(command, LanguageCommand) and command.locale is None:
            # Dedicated language-selection list (spec 0010, RQ-LNG-004).
            self._start_language_flow()
            return
        if (
            isinstance(command, LanguageCommand)
            and command.locale is not None
            and self._language_selection is not None
        ):
            # An explicit locale code satisfies the open selection too: close
            # the list and let the normal dispatch persist it. First-run
            # resumes onboarding once the write succeeds.
            self._resume_onboarding = self._language_first_run
            self._close_language_list()
        # Context-aware availability: keep the action discoverable but explain
        # the prerequisite instead of failing silently.
        availability = self._check_availability(command)
        if availability is not None:
            self._emit(availability)
            return
        if isinstance(command, ExamineStartCommand):
            self._open_exam_preparation()
            return
        if isinstance(command, ExamineFinishCommand):
            self._open_finish_confirmation()
            return
        if isinstance(command, EvaluateCommand):
            self._confirm_then_run(command)
            return
        self._run_nonblocking(command)

    def _check_availability(self, command: Command) -> str | None:
        """Return a prerequisite explanation when an action cannot run now."""
        from ..action_registry import check_availability

        action_id = _COMMAND_ACTION_IDS.get(type(command))
        if action_id is None:
            return None
        project = None
        with contextlib.suppress(Exception):
            project = self.router.context.project_id or getattr(
                self.router.config.project, "path", None
            )
        exam_active = False
        with contextlib.suppress(Exception):
            status = self._exam_status()
            exam_active = bool(status is not None and status.is_active)
        # An explicit project path set via --project counts even before URN.
        if not project:
            with contextlib.suppress(Exception):
                project = str(self.router.config.project.path)
        available, reason = check_availability(
            action_id,
            project_path=project,
            exam_active=exam_active,
            locale=self._current_locale(),
        )
        # Empty-text prerequisites for free-text actions (spec 0011 REQ-003):
        # required input is explained even when the action is otherwise
        # available, so the student is never left at a blank prompt.
        if isinstance(command, AskCommand) and not command.question.strip():
            from ...locale.ui_strings import get_ui_string

            return get_ui_string("prereq_question", self._current_locale())
        if isinstance(command, ExamplesCommand) and not command.topic.strip():
            from ...locale.ui_strings import get_ui_string

            return get_ui_string("prereq_topic", self._current_locale())
        if isinstance(command, ExamineStartCommand) and not command.statement.strip():
            from ...locale.ui_strings import get_ui_string

            return get_ui_string("prereq_statement", self._current_locale())
        if available:
            return None
        return reason or "Action unavailable."

    # ------------------------------------------------------------------
    # Dedicated language-selection list (spec 0010, RQ-LNG-004/005/006)
    # ------------------------------------------------------------------

    def _start_language_flow(self, *, first_run: bool = False) -> None:
        """Open the navigable Español/English list.

        The cursor initially focuses the saved locale when one exists;
        otherwise the deterministic default is focused — but focusing never
        counts as a choice: the student must press Enter explicitly.
        """
        from ...locale.selection import LanguageSelection
        from ...locale.ui_strings import get_ui_string

        saved = None
        getter = getattr(self.router, "saved_locale", None)
        if callable(getter):
            with contextlib.suppress(Exception):
                saved = getter()
        self._language_selection = LanguageSelection.with_focus(saved)
        self._language_first_run = first_run
        self._pending_language = True
        locale = self._current_locale()
        self._status(get_ui_string("locale_label", locale))
        with contextlib.suppress(Exception):
            language_list = self.query_one("#language-list", LanguageList)
            language_list.show(
                self._language_selection,
                title=get_ui_string("lang_list_title", locale),
                hints=get_ui_string("lang_list_hints", locale),
            )
            # The list owns the keyboard while open (Up/Down/Enter/Esc/q);
            # focus it after any other refresh so keys reach the widget.
            language_list.focus()

    def _close_language_list(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#language-list", LanguageList).hide()
        self._language_selection = None
        self._pending_language = False
        self._language_first_run = False

    def _confirm_focused_language(self) -> None:
        """Persist the focused locale; refresh; confirm in the new language."""
        if self._language_selection is None:
            return
        if self.ui_state.busy:
            from ...locale.ui_strings import get_ui_string

            self._emit(get_ui_string("busy_blocked", self._current_locale()))
            return
        locale = self._language_selection.confirm()
        first_run = self._language_first_run
        self._close_language_list()
        # Continue to onboarding once the first-run locale persists; the flag
        # is consumed after the worker confirms the write succeeded.
        self._resume_onboarding = first_run
        # Reuse the normal dispatch path so persistence, refresh, and the
        # localized confirmation stay centralized in the router.
        self._handle_command(LanguageCommand(locale=locale))
        self._focus_input()

    def _cancel_language_flow(self) -> None:
        """Cancel without changing the saved locale (RQ-LNG-005)."""
        from ...locale.ui_strings import get_ui_string

        if self._language_selection is None:
            return
        if self._language_first_run:
            # First-run onboarding stays blocked until an explicit choice;
            # keep the list open instead of silently assigning a default.
            self._emit(get_ui_string("lang_first_run_blocked", self._current_locale()))
            with contextlib.suppress(Exception):
                self.query_one("#language-list", LanguageList).focus()
            return
        self._close_language_list()
        self._emit(get_ui_string("lang_cancelled", self._current_locale()))
        self._status("Ready")
        self._focus_input()

    @on(LanguageList.Confirmed)
    def on_language_confirmed(self, message: LanguageList.Confirmed) -> None:
        if self._language_selection is None:
            return
        # The widget already recorded the explicit confirmation.
        self._confirm_focused_language()

    @on(LanguageList.Cancelled)
    def on_language_cancelled(self, message: LanguageList.Cancelled) -> None:
        self._cancel_language_flow()

    # ------------------------------------------------------------------
    # Confirmation for Gradle-scope and exam actions
    # (RQ-TUI-013 / 014, RQ-EXM-003 / 004)
    # ------------------------------------------------------------------

    def _confirm_then_run(self, command: Command) -> None:
        """Require an explicit confirmation before a consequential action.

        ``/evaluate`` runs Gradle; ``/exam-init`` starts an exam; ``/exam-finish``
        scores and closes the active exam. Each is confirmed unless it already
        carries an explicit ``yes``.
        """
        if getattr(command, "confirmed", False):
            self._set_confirmation_visible(False)
            self._run_nonblocking(command)
            return
        self._pending_exam = command
        self.ui_state.view = _CONFIRM_VIEW.get(type(command), View.EVALUATE)
        self._pending_eval = command if isinstance(command, EvaluateCommand) else None
        self._status(get_ui_string("waiting_confirmation", self._current_locale()))
        if not (
            isinstance(command, ExamineStartCommand) and self._exam_start_offer_shown
        ):
            self._emit(self._confirm_prompt(command))
        self._set_confirmation_visible(True)

    def _open_exam_preparation(self) -> None:
        """Show read-only readiness and the compact start/back selector."""
        getter = getattr(self.router, "exam_preparation_status", None)
        if not callable(getter):
            return
        status = getter()
        self._exam_preparing = True
        self.ui_state.view = View.EXAM_START
        self.query_one("#exam-preparation-list", ExamPreparationList).show(
            status, locale=self._current_locale()
        )
        self._emit_preparation_blockers(status)

    def _emit_preparation_blockers(self, status) -> None:
        """Explain, in the conversation log, why the exam cannot start yet.

        The panel stays compact so ``Empezar examen`` is always visible; the
        full, localized reasons (and how to fix each one) live in the scrollable
        log instead of being clipped by the panel's height (RQ-EXM-036/045).
        Re-emitted only when the set of blockers changes, so re-opening the
        panel does not spam the conversation.
        """
        if status.ready_to_start:
            self._exam_prep_signature = None
            return
        signature = tuple(status.blockers)
        if signature == self._exam_prep_signature:
            return
        self._exam_prep_signature = signature
        locale = self._current_locale()
        self._emit(get_ui_string("exam_start_blocked", locale))
        for code in status.blockers:
            detail = (
                status.toolchain_blockers[0]
                if code == "toolchain_not_ready" and status.toolchain_blockers
                else ""
            )
            self._emit("- " + describe_blocker(code, locale, detail=detail))

    def _close_exam_preparation(self) -> None:
        self._exam_preparing = False
        with contextlib.suppress(Exception):
            self.query_one("#exam-preparation-list", ExamPreparationList).hide()
        self._focus_input()

    def _open_finish_confirmation(self) -> None:
        """Present the required compact finish/continue confirmation."""
        self._exam_preparing = False
        self.ui_state.view = View.EXAM_FINISH
        self.query_one("#exam-preparation-list", ExamPreparationList).show_finish(
            locale=self._current_locale()
        )

    @on(ExamPreparationList.Confirmed)
    def on_exam_preparation_confirmed(
        self, message: ExamPreparationList.Confirmed
    ) -> None:
        if message.option == "finish":
            self._close_exam_preparation()
            self._run_nonblocking(ExamineFinishCommand(yes=True))
            return
        if message.option == "continue":
            self._close_exam_preparation()
            return
        if message.option == "back":
            self._close_exam_preparation()
            return
        getter = getattr(self.router, "exam_preparation_status", None)
        status = getter() if callable(getter) else None
        if status is None or not status.ready_to_start:
            self._open_exam_preparation()
            return
        self._close_exam_preparation()
        self._run_nonblocking(
            ExamineStartCommand(statement=status.instructions_path or "", yes=True)
        )

    @on(ExamPreparationList.Cancelled)
    def on_exam_preparation_cancelled(
        self, _message: ExamPreparationList.Cancelled
    ) -> None:
        self._close_exam_preparation()

    def _show_exam_start_offer(self) -> None:
        """Open Start exam confirmation as soon as the action is selected.

        The controls appear before any pending command exists so the student
        can still type the exam statement. Confirm validates that input (or
        the already-pending command) and only then runs the action.
        """
        self._pending_exam = None
        self._pending_eval = None
        self.ui_state.view = View.EXAM_START
        self._status(get_ui_string("waiting_confirmation", self._current_locale()))
        if not self._exam_start_offer_shown:
            self._emit(
                self._confirm_prompt(
                    ExamineStartCommand(statement=self._exam_start_statement())
                )
            )
            self._exam_start_offer_shown = True
        self._set_confirmation_visible(True)

    def _exam_start_statement(self) -> str:
        with contextlib.suppress(Exception):
            return (self.query_one("#input", PromptArea).text or "").strip()
        return ""

    def _clear_input(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#input", PromptArea).clear()

    def _set_confirmation_visible(self, visible: bool) -> None:
        """Show/hide the shared Confirm/Cancel buttons and localize labels."""
        locale = self._current_locale()
        with contextlib.suppress(Exception):
            bar = self.query_one("#confirm-bar")
            bar.display = visible
            if visible:
                self.query_one("#confirm-yes", Button).label = get_ui_string(
                    "confirm_yes", locale
                )
                self.query_one("#confirm-no", Button).label = get_ui_string(
                    "confirm_no", locale
                )

    def _confirm_prompt(self, command: Command) -> str:
        """Localized confirmation guidance for ``command``.

        Exam start/finish prompts explain what the action will do, how to
        configure the exam, and exactly how to confirm or cancel.
        """
        key = _CONFIRM_STRING_KEYS.get(type(command))
        if key is not None:
            return get_ui_string(key, self._current_locale())
        return _CONFIRM_PROMPT[type(command)]

    def _resolve_pending_exam(self, pending: Command, answer: str) -> None:
        self._pending_exam = None
        self._pending_eval = None
        self._exam_start_offer_shown = False
        self.ui_state.view = View.CHAT
        self._set_confirmation_visible(False)
        if answer.strip().lower() in {"y", "yes"}:
            self._run_nonblocking(pending)
        else:
            locale = self._current_locale()
            self._status(get_ui_string("ready", locale))
            self._emit(
                get_ui_string(_ABORT_STRING_KEYS[type(pending)], locale)
                if type(pending) in _ABORT_STRING_KEYS
                else _ABORT_ECHO[type(pending)]
            )
            self._focus_input()

    @on(Button.Pressed, "#confirm-yes")
    def _confirm_pressed(self) -> None:
        if self.ui_state.busy:
            self._emit(get_ui_string("busy_blocked", self._current_locale()))
            return
        pending = self._pending_exam
        if isinstance(pending, ExamineStartCommand) or (
            pending is None and self.ui_state.action == "exam-init"
        ):
            self._confirm_exam_start(pending)
            return
        if pending is not None:
            self._resolve_pending_exam(pending, "yes")

    def _confirm_exam_start(self, pending: Command | None) -> None:
        """Validate student, exam instructions, and project before starting."""
        statement = self._exam_start_statement()
        if not statement and isinstance(pending, ExamineStartCommand):
            statement = pending.statement
        issues = self._validate_exam_start(statement)
        if issues:
            self._emit_exam_start_issues(issues)
            if statement:
                # Keep the edited statement so the next click can proceed.
                self._pending_exam = ExamineStartCommand(statement=statement)
            return
        command = ExamineStartCommand(statement=statement)
        self._clear_input()
        self._resolve_pending_exam(command, "yes")

    def _validate_exam_start(self, statement: str) -> list[str]:
        """Return every blocking reason for starting the exam, localized."""
        locale = self._current_locale()
        issues: list[str] = []
        if self.ui_state.awaiting_name or not self.router.context.student_id:
            issues.append(get_ui_string("exam_start_no_student", locale))
        text = statement.strip()
        if not text:
            issues.append(get_ui_string("prereq_statement", locale))
        else:
            path = Path(text).expanduser()
            try:
                from ...exams.definition import ExamDefinitionLoader

                loader = ExamDefinitionLoader()
                if text.startswith("{"):
                    loader.load_text(text, exam_id=None)
                elif path.is_file():
                    loader.load(path, exam_id=None)
                else:
                    issues.append(
                        get_ui_string("exam_statement_not_found", locale).format(
                            detail=path
                        )
                    )
            except Exception as exc:  # noqa: BLE001 - report, never crash
                issues.append(
                    get_ui_string("exam_statement_invalid", locale).format(
                        detail=str(exc)
                    )
                )
        try:
            readiness = self.router.check_project_readiness()
        except Exception as exc:  # noqa: BLE001 - report, never crash
            issues.append(f"{get_ui_string('preflight_failed', locale)} {exc}")
        else:
            if not readiness.ready:
                for issue in readiness.issues:
                    issues.append(
                        describe_blocker(issue.code, locale, detail=issue.detail)
                    )
        return issues

    def _emit_exam_start_issues(self, issues: list[str]) -> None:
        locale = self._current_locale()
        self._emit(get_ui_string("exam_start_blocked", locale))
        for issue in issues:
            self._emit("- " + issue)
        self._status(get_ui_string("waiting_confirmation", locale))
        self._focus_input()

    @on(Button.Pressed, "#confirm-no")
    def _cancel_pressed(self) -> None:
        if self._pending_exam is not None:
            self._resolve_pending_exam(self._pending_exam, "no")
            return
        if self.ui_state.action != "exam-init":
            return
        self._clear_input()
        self._exam_start_offer_shown = False
        self._set_confirmation_visible(False)
        self._status(get_ui_string("ready", self._current_locale()))
        self._emit(
            get_ui_string(
                _ABORT_STRING_KEYS[ExamineStartCommand], self._current_locale()
            )
        )
        self._focus_input()

    #: Backward-compatible alias for the evaluate-only flow.
    _resolve_pending_eval = _resolve_pending_exam

    # ------------------------------------------------------------------
    # Non-blocking dispatch (RQ-TUI-016 / 017)
    # ------------------------------------------------------------------

    def _run_nonblocking(self, command: Command) -> None:
        status = _RUN_STATUS.get(type(command), "Running")
        self._current_kind = _COMMAND_KINDS.get(type(command), MessageKind.SYSTEM)
        self._last_action_id = _COMMAND_ACTION_IDS.get(type(command))
        # Cleared before the worker starts so an abort from a previous run
        # cannot be mistaken for one against this command.
        self.ui_state.cancelled = False
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
        # Long-running actions report localized progress through this sink while
        # the worker runs (RQ-EXM-048).
        self.router.progress = self._emit_progress
        if isinstance(command, ExamineStartCommand):
            readiness = self.router.check_project_readiness()
            if not readiness.ready:
                return ErrorResponse(message=self._readiness_message(readiness))
        return self.router.dispatch(command)

    def _emit_progress(self, text: str) -> None:
        """Post one progress line from a worker thread (thread-safe).

        ``post_message`` schedules the update on the UI thread, so the worker
        never mutates presentation state directly (RQ-EXM-048).
        """
        if text:
            self.post_message(OutputReady(text, kind=MessageKind.SYSTEM))

    def _readiness_message(self, readiness) -> str:
        """Localized explanation of every blocking project-readiness issue."""
        locale = self._current_locale()
        lines = [get_ui_string("preflight_failed", locale)]
        for issue in readiness.issues:
            reason = describe_blocker(issue.code, locale, detail=issue.detail)
            lines.append(f"- {reason}")
        return "\n".join(lines)

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
            self._emit_recommendation(result)
            if self._last_action_id == "language":
                self._resume_onboarding = False
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
            self._emit_recommendation(result)
            if isinstance(result, ExamFinishResult):
                self._open_exam_report(result)
        notice = self.router.context_notice()
        if notice:
            self._emit("Note: " + self.formatter.error(notice))
        # Locale may have changed (language action): refresh selector labels
        # and hints without touching progress/attempts. Stage/version refresh
        # happens inside refresh_session_bar (persisted sources only).
        self._refresh_selector_labels()
        self._apply_action_prompt()
        self.refresh_session_bar()
        self._sync_exam_timer()
        # First-run language gate: continue to onboarding once the locale
        # write succeeded (RQ-LNG-002).
        if self._resume_onboarding and self._last_action_id == "language":
            self._resume_onboarding = False
            self._maybe_start_onboarding()
        self._focus_input()

    def _open_exam_report(self, result: ExamFinishResult) -> None:
        """Open the generated PDF with the OS viewer, best-effort (RQ-EXM-049).

        Controlled by ``tools.open_report``; a missing viewer never affects the
        result or the conversation.
        """
        path = getattr(result, "report_path", None)
        if not path:
            return
        try:
            enabled = bool(self.router.config.tools.open_report)
        except Exception:  # noqa: BLE001 - never break the result display
            enabled = True
        if enabled:
            open_path(path)

    def _emit_recommendation(self, result: CommandResult) -> None:
        """Emit one validated next-step recommendation, or a neutral invite.

        Spec 0011 §5: at most one justified recommendation with a stable action
        id; never auto-executed (the student selects it explicitly), never a
        progression change. When nothing is justified, invite the student to
        choose another action instead of inventing one.
        """
        from ...locale.ui_strings import get_ui_string

        suggest = getattr(self.router, "suggest_next", None)
        if not callable(suggest):
            return
        try:
            recommendation = suggest(self._last_action_id, result)
        except Exception:  # noqa: BLE001 - guidance must never break results
            return
        locale = self._current_locale()
        if recommendation is None:
            self._emit(get_ui_string("no_next_step", locale))
            return
        try:
            self._emit(recommendation.display(locale))
        except Exception:  # noqa: BLE001
            return

    def on_output_ready(self, message: OutputReady) -> None:
        self._enqueue_output(message.kind, message.text)

    # ------------------------------------------------------------------
    # Conversation rendering (RQ-TUI-034)
    # ------------------------------------------------------------------

    #: Characters revealed per animation tick when streaming ADA Sensei output.
    _STREAM_CHARS = 24
    #: Seconds between stream ticks (lightweight, event-loop driven).
    _STREAM_INTERVAL = 0.03

    def _scroll_log_end(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#log", RichLog).scroll_end(animate=False)

    def _enqueue_output(self, kind: MessageKind, text: str) -> None:
        """Append an entry, animating ADA Sensei responses as a typing stream.

        Animation simulates the agent thinking/writing: text is revealed
        progressively while the log scrolls to keep the latest text visible.
        """
        if not text:
            return
        try:
            log = self.query_one("#log", RichLog)
        except Exception:
            return
        if kind is MessageKind.SYSTEM:
            log.write(text)
            self._scroll_log_end()
            return
        label = MESSAGE_LABELS.get(kind)
        width = max((log.size.width or 60), 12)
        if label:
            log.write(Text(f"  {label}\n", style="bold"))
            log.write(Text("  " + "─" * max(width - 2, 1) + "\n", style="dim"))
        self._scroll_log_end()
        # Stream ADA Sensei/result messages progressively; show user echoes instantly.
        if kind is MessageKind.USER or "```" in text:
            self._write_body(log, text)
            self._scroll_log_end()
            return
        self._stream_body(text)

    def _stream_body(self, text: str) -> None:
        """Progressively reveal ``text`` into the log, scrolling as it grows."""
        if not hasattr(self, "_stream_queue"):
            self._stream_queue = []
            self._stream_timer = None
        self._stream_queue.append(text)
        if self._stream_timer is None and self._is_mounted:
            with contextlib.suppress(Exception):
                self._stream_timer = self.set_interval(
                    self._STREAM_INTERVAL, self._advance_stream, name="output-stream"
                )
        if self._stream_timer is None:
            # Not mounted (e.g. tests): render immediately.
            while self._stream_queue:
                with contextlib.suppress(Exception):
                    log = self.query_one("#log", RichLog)
                    log.write(Text(self._stream_queue.pop(0)))
            self._scroll_log_end()

    def _advance_stream(self) -> None:
        """Reveal the next chunk of the streaming output queue."""
        queue = getattr(self, "_stream_queue", None)
        if not queue:
            timer = getattr(self, "_stream_timer", None)
            if timer is not None:
                with contextlib.suppress(Exception):
                    timer.stop()
            self._stream_timer = None
            return
        try:
            log = self.query_one("#log", RichLog)
        except Exception:
            self._stream_queue = []
            return
        current = queue[0]
        n = min(self._STREAM_CHARS, len(current))
        chunk = current[:n]
        remaining = current[n:]
        if chunk:
            log.write(Text(chunk))
            self._scroll_log_end()
        if remaining:
            queue[0] = remaining
        else:
            queue.pop(0)
            log.write(Text("\n"))
            self._scroll_log_end()
        if not queue:
            timer = getattr(self, "_stream_timer", None)
            if timer is not None:
                with contextlib.suppress(Exception):
                    timer.stop()
            self._stream_timer = None

    def _write_output(self, kind: MessageKind, text: str) -> None:
        """Compatibility wrapper: append an entry to the log."""
        self._enqueue_output(kind, text)

    def _write_body(self, log: RichLog, text: str) -> None:
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
