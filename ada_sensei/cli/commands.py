"""Typed command objects and result types for the CLI and TUI.

This module defines the single command vocabulary shared by the direct CLI and
the interactive TUI (RQ-CLI-004). Both interfaces build the same command
objects, which are then dispatched through the shared :class:`CommandRouter`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..actions.ask import AskResult
from ..actions.evaluate import EvalResult
from ..actions.examine import ExamFinishResult, ExamStartResult
from ..actions.examples import ExamplesResult
from ..actions.practice import PracticeResult
from ..models import Answer, ExampleResult


@dataclass
class PracticeCommand:
    """Request to generate an exercise."""

    topic: str | None = None
    difficulty: str | None = None
    objective: str | None = None
    adaptive: bool = True


@dataclass
class AskCommand:
    """Request to answer a question."""

    question: str
    #: Optional cooperative-cancellation probe. The TUI passes one so a run the
    #: student aborts is recorded as cancelled rather than completed, and is
    #: therefore not charged to the exam ask allowance (RQ-EXM-005).
    is_cancelled: Callable[[], bool] | None = None


@dataclass
class ExamplesCommand:
    """Request to produce a teachable example."""

    topic: str
    level: str = "basic"
    teacher: bool = False


@dataclass
class EvaluateCommand:
    """Request to evaluate the student's project.

    ``exercise_id`` selects the exercise explicitly (RQ-CLI-010). ``yes``
    carries the non-interactive confirmation override (RQ-CLI-016). ``instrumented``
    is reserved and rejected (RQ-CLI-015).
    """

    exercise_id: str | None = None
    yes: bool = False
    instrumented: bool = False

    @property
    def confirmed(self) -> bool:
        return self.yes


@dataclass
class ExamineStartCommand:
    """Request to start an exam (``/exam-init``).

    ``statement`` is the instructor statement: a path, a Markdown/structured
    definition, or inline text. Identity is never read from it (RQ-EXM-001);
    ``student_id``/``project_id`` only override the session values explicitly.
    ``yes`` carries the non-interactive start confirmation (RQ-EXM-003).
    """

    statement: str = ""
    student_id: str | None = None
    project_id: str | None = None
    exercise_id: str | None = None
    yes: bool = False

    @property
    def confirmed(self) -> bool:
        return self.yes


@dataclass
class ExamineFinishCommand:
    """Request to finish the active exam.

    ``yes`` carries the non-interactive finish confirmation (RQ-EXM-004) and
    ``instrumented`` is reserved and rejected, mirroring ``/evaluate``
    (RQ-EXM-011).
    """

    yes: bool = False
    instrumented: bool = False

    @property
    def confirmed(self) -> bool:
        return self.yes


@dataclass
class ProjectCommand:
    """Request to set / display the active project."""

    path: str | None = None


@dataclass
class HintCommand:
    """Request to reveal the next hint (delegated to the action layer)."""


@dataclass
class MoreCommand:
    """Request to advance the assistance level (delegated to the action layer)."""


@dataclass
class SolutionCommand:
    """Request to jump to the solution level (delegated to the action layer)."""


@dataclass
class HelpCommand:
    """Request to show help.

    ``scope`` is ``None`` for global help or the action name for action help.
    """

    scope: str | None = None


@dataclass
class ClearCommand:
    """Request to clear the presentation view (TUI only, no domain effect)."""


@dataclass
class QuitCommand:
    """Request to exit the CLI/TUI cleanly."""


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ExamStatus:
    """Authoritative exam status for display (RQ-EXM-005, RQ-EXM-007).

    Every field is read from the persisted attempt and its event log, never from
    presentation state or model output. ``allowed_*`` fields are ``None`` when
    the exam defines no limit, which is the case the TUI renders as ``—``.
    """

    exam_attempt_id: str
    exam_id: str
    ask_count: int
    allowed_ask_count: int | None = None
    duration_seconds: int | None = None
    allowed_duration_seconds: int | None = None
    is_completed: bool = False

    @property
    def is_active(self) -> bool:
        return not self.is_completed


@dataclass
class ProjectResult:
    """Result of configuring the active project."""

    path: str | None
    project_id: str | None


@dataclass
class AssistanceResult:
    """Result of a progressive-assistance request (delegated)."""

    answer: Answer | None = None
    level: str | None = None
    message: str = ""


@dataclass
class HelpResult:
    """Formatted help text."""

    text: str


@dataclass
class ClearResult:
    """Acknowledgment that the view was cleared (presentation only)."""


@dataclass
class QuitResult:
    """Signal that the session should exit."""


@dataclass
class MetaResult:
    """A generic acknowledged meta operation (e.g. context reduction notice)."""

    message: str = ""


@dataclass
class ErrorResponse:
    """An expected, user-presentable error."""

    message: str


@dataclass
class InternalFailure:
    """An unexpected, sanitized failure."""

    message: str


@dataclass
class LanguageCommand:
    """Display or change the interface language (spec 0010).

    ``locale`` is None to show the current locale, or a locale string
    (``es-CO`` or ``en-US``) to change it.
    """

    locale: str | None = None


@dataclass
class LearnCommand:
    """Request to learn / review the current stage concepts (spec 008)."""

    topic: str | None = None


@dataclass
class DiagnoseCommand:
    """Request an initial or in-stage diagnostic (spec 008)."""

    stage_id: str | None = None



CommandResult = (
    PracticeResult
    | AskResult
    | Answer
    | ExampleResult
    | ExamplesResult
    | EvalResult
    | ExamStartResult
    | ExamFinishResult
    | ProjectResult
    | AssistanceResult
    | HelpResult
    | ClearResult
    | QuitResult
    | MetaResult
    | ErrorResponse
    | InternalFailure
)

#: Types that represent successful completion without a payload to format.
SENTINEL_RESULTS = (ClearResult, QuitResult)

#: Aliased for backward-compatible naming in the router.
Command = (
    PracticeCommand
    | AskCommand
    | ExamplesCommand
    | EvaluateCommand
    | ExamineStartCommand
    | ExamineFinishCommand
    | ProjectCommand
    | HintCommand
    | MoreCommand
    | SolutionCommand
    | HelpCommand
    | ClearCommand
    | QuitCommand
    | LanguageCommand
    | LearnCommand
    | DiagnoseCommand
)
