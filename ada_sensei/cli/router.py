"""CommandRouter — the single boundary between presentation and application.

Both the direct CLI (cli/app.py) and the interactive TUI (cli/tui/) build typed
command objects (cli/commands.py) and dispatch them here. The router maps each
command type to the corresponding application action (RQ-CLI-005) and marshals
the result into a :class:`CommandResult`. The router contains no action business
logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..actions.ask import AskAction
from ..actions.base import ActionServices
from ..actions.evaluate import (
    EvaluateAction,
    EvaluateInput,
    EvaluationAborted,
    InstrumentedNotSupportedError,
)
from ..actions.examples import ExamplesAction
from ..actions.practice import PracticeAction, PracticeInput
from ..config import Config, ConfigLoader, Secrets
from ..context import SessionContext
from ..llm.base import LLMClient
from ..llm.ollama import OllamaProvider
from ..urns import URN
from .commands import (
    AskCommand,
    AssistanceResult,
    ClearCommand,
    ClearResult,
    Command,
    CommandResult,
    ErrorResponse,
    EvaluateCommand,
    ExamplesCommand,
    HelpCommand,
    HelpResult,
    HintCommand,
    InternalFailure,
    MoreCommand,
    PracticeCommand,
    ProjectCommand,
    ProjectResult,
    QuitCommand,
    QuitResult,
    SolutionCommand,
)
from .errors import CLIError


class CommandRouter:
    """Bridges a parsed :class:`Command` to the correct application action.

    ``dispatch`` never raises for expected user errors; it returns an
    :class:`ErrorResponse` (or :class:`InternalFailure`) as a result so both the
    CLI and the TUI can render it uniformly.
    """

    def __init__(
        self,
        config: Config | None = None,
        config_file: str | Path | None = None,
        env: dict[str, str] | None = None,
        client: Any = None,
    ) -> None:
        if config is None:
            loader = ConfigLoader(env=env)
            config = loader.load(config_file=config_file)
        if config.data_dir is None or not Path(config.data_dir).exists():
            Path(config.data_dir or config.resolved_data_dir).mkdir(
                parents=True, exist_ok=True
            )
        self.config = config
        self.env = env
        self.secrets = Secrets.from_config(config, env=env)
        self.context = SessionContext(config=config, data_dir=config.resolved_data_dir)
        self.client: LLMClient | None = client or self._build_client()

    def _build_client(self) -> LLMClient:
        cfg = self.config.llm
        if cfg.provider != "ollama":
            raise CLIError(f"unsupported LLM provider: {cfg.provider!r}")
        return OllamaProvider(
            base_url=cfg.base_url,
            api_key=self.secrets.get("api_key"),
            timeout_seconds=cfg.timeout_seconds,
            temperature=cfg.temperature,
        )

    def services(self) -> Any:
        return ActionServices.build(self.config, self.context, self.client)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, command: Command) -> CommandResult:
        """Dispatch a command object to its action and return a result."""
        try:
            if isinstance(command, PracticeCommand):
                return self._practice(command)
            if isinstance(command, AskCommand):
                return self._ask(command)
            if isinstance(command, ExamplesCommand):
                return self._examples(command)
            if isinstance(command, EvaluateCommand):
                return self._evaluate(command)
            if isinstance(command, ProjectCommand):
                return self._project(command)
            if isinstance(command, (HintCommand, MoreCommand, SolutionCommand)):
                return self._assist(command)
            if isinstance(command, HelpCommand):
                return HelpResult(text=self._help_text(command.scope))
            if isinstance(command, ClearCommand):
                return ClearResult()
            if isinstance(command, QuitCommand):
                return QuitResult()
        except CLIError as exc:
            return ErrorResponse(message=str(exc))
        except (EvaluationAborted, InstrumentedNotSupportedError,
                NotImplementedError) as exc:
            return ErrorResponse(message=str(exc))
        except (ValueError, LookupError) as exc:
            return ErrorResponse(message=str(exc))
        except Exception as exc:
            return InternalFailure(message=self._sanitize(exc))
        return InternalFailure(message="unsupported command type")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _practice(self, cmd: PracticeCommand) -> CommandResult:
        try:
            pin = PracticeInput.from_options(
                topic=cmd.topic,
                difficulty=cmd.difficulty,
                objective=cmd.objective,
                adaptive=cmd.adaptive,
            )
        except ValueError as exc:
            return ErrorResponse(message=str(exc))
        return PracticeAction(self.services()).run(pin)

    def _ask(self, cmd: AskCommand) -> CommandResult:
        if not cmd.question.strip():
            return ErrorResponse(message="ask requires a question")
        return AskAction(self.services()).run(cmd.question)

    def _examples(self, cmd: ExamplesCommand) -> CommandResult:
        if not cmd.topic.strip():
            return ErrorResponse(message="examples requires a <topic>")
        return ExamplesAction(self.services()).run(
            cmd.topic,
            level=cmd.level,
            teacher=cmd.teacher,
        )

    def _evaluate(self, cmd: EvaluateCommand) -> CommandResult:
        return EvaluateAction(self.services()).run(
            EvaluateInput(
                exercise_id=cmd.exercise_id,
                instrumented=cmd.instrumented,
                confirmed=cmd.confirmed,
            )
        )

    def _project(self, cmd: ProjectCommand) -> CommandResult:
        if cmd.path:
            path = str(Path(cmd.path).expanduser().resolve())
            self.context.set_project(path)
            return ProjectResult(path=path, project_id=self.context.project_id)
        path = str(self.config.project.path)
        project_id = (
            URN.project_id_from_path(str(Path(path).resolve()))
            if path not in ("", ".")
            else None
        )
        return ProjectResult(path=path, project_id=project_id)

    def _assist(self, cmd: Command) -> CommandResult:
        name = {
            HintCommand: "hint",
            MoreCommand: "more",
            SolutionCommand: "solution",
        }.get(type(cmd), "more")
        try:
            result = AskAction(self.services()).escalate(name)
        except LookupError as exc:
            return ErrorResponse(message=str(exc))
        return AssistanceResult(answer=result.answer, message="")

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _help_text(self, scope: str | None) -> str:
        from .parser import CommandParser

        return CommandParser.command_help()

    def _sanitize(self, exc: Exception) -> str:
        return self.secrets.redact(f"{type(exc).__name__}: {exc}")

    def context_notice(self) -> str | None:
        """Return a context-reduction notice (RQ-CLI-020) if the last action
        surfaced one. Currently the foundation's ContextManager is not wired to
        the actions, so this returns None until that plumbing lands."""
        notice = getattr(self, "_last_notice", None)
        return notice


# Backward-compatible alias
Router = CommandRouter

__all__ = ["CommandRouter", "Router"]
