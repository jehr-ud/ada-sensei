"""Typed command objects and result types for the CLI and TUI.

This module defines the single command vocabulary shared by the direct CLI and
the interactive TUI (RQ-CLI-004). Both interfaces build the same command
objects, which are then dispatched through the shared :class:`CommandRouter`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..actions.ask import AskResult
from ..actions.evaluate import EvalResult
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


CommandResult = (
    PracticeResult
    | AskResult
    | Answer
    | ExampleResult
    | ExamplesResult
    | EvalResult
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
    | ProjectCommand
    | HintCommand
    | MoreCommand
    | SolutionCommand
    | HelpCommand
    | ClearCommand
    | QuitCommand
)


class CommandOutcome:
    @staticmethod
    def is_error(result: CommandResult) -> bool:
        """Return True when the result is an error/failure to be reported."""
        return isinstance(result, (ErrorResponse, InternalFailure))

    @staticmethod
    def unwrap(result: CommandResult) -> Any:
        """Return the underlying presentable value for formatting."""
        return result
