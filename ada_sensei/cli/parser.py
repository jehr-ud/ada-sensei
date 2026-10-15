"""Parse user input (argv or slash line) into typed command objects.

Both the direct CLI (``cli/app.py``) and the interactive TUI (``cli/tui/``)
call these helpers. They produce the shared command objects from
``cli/commands.py`` so the CommandRouter dispatches the same commands
regardless of the presentation mode (RQ-CLI-004).
"""

from __future__ import annotations

from typing import Any

from .commands import (
    AskCommand,
    ClearCommand,
    Command,
    EvaluateCommand,
    ExamineFinishCommand,
    ExamineStartCommand,
    ExamplesCommand,
    HelpCommand,
    HintCommand,
    MoreCommand,
    PracticeCommand,
    ProjectCommand,
    QuitCommand,
    SolutionCommand,
)
from .errors import CLIError

AVAILABLE_ACTIONS = (
    "practice",
    "ask",
    "examples",
    "evaluate",
    "exam-init",
    "exam-finish",
)

SLASH_COMMANDS = (
    "help",
    "exit",
    "quit",
    "project",
    "hint",
    "more",
    "solution",
    "clear",
)


class CommandParser:
    @staticmethod
    def _parse_flags(value: list[str]) -> tuple[dict[str, Any], list[str]]:
        """Parse --flag value pairs and positionals into options + positional args."""
        options: dict[str, Any] = {}
        positional: list[str] = []
        i = 0
        while i < len(value):
            token = value[i]
            if token == "--":
                positional.extend(value[i + 1 :])
                break
            if token.startswith("--"):
                name = token[2:]
                if "=" in name:
                    key, val = name.split("=", 1)
                    options[key] = val
                    i += 1
                    continue
                if name == "no-adaptive":
                    options["adaptive"] = False
                    i += 1
                    continue
                if i + 1 < len(value) and not value[i + 1].startswith("--"):
                    options[name] = value[i + 1]
                    i += 2
                else:
                    options[name] = True
                    i += 1
                continue
            positional.append(token)
            i += 1
        return options, positional

    @staticmethod
    def _action_command(
        action: str, options: dict[str, Any], positional: list[str]
    ) -> Command:
        if action == "practice":
            return PracticeCommand(
                topic=options.get("topic"),
                difficulty=options.get("difficulty"),
                objective=options.get("objective"),
                adaptive=bool(options.get("adaptive", True)),
            )
        if action == "ask":
            return AskCommand(question=" ".join(positional))
        if action == "examples":
            return ExamplesCommand(
                topic=positional[0] if positional else "",
                level=options.get("level", "basic"),
                teacher=bool(options.get("teacher", False)),
            )
        if action == "evaluate":
            return EvaluateCommand(
                exercise_id=options.get("exercise"),
                yes=bool(options.get("yes", False)),
                instrumented=bool(options.get("instrumented", False)),
            )
        if action == "exam-init":
            # RQ-EXM-001: identity is never read from the statement. The
            # statement is a path, a structured definition, or inline text.
            return ExamineStartCommand(
                statement=" ".join(positional),
                student_id=options.get("student"),
                project_id=options.get("project-id"),
                exercise_id=options.get("exercise"),
                yes=bool(options.get("yes", False)),
            )
        if action == "exam-finish":
            return ExamineFinishCommand(
                yes=bool(options.get("yes", False)),
                instrumented=bool(options.get("instrumented", False)),
            )
        raise CLIError(f"unknown action: {action!r}")

    @classmethod
    def parse_argv(cls, argv: list[str]) -> Command:
        """Parse direct-invocation argv into a typed command object."""
        argv = list(argv)

        # Global options may appear anywhere; strip the recognized ones. They
        # only apply to the session through app.py (RQ-CLI-007), not here.
        rest: list[str] = []
        i = 0
        while i < len(argv):
            tok = argv[i]
            if tok == "--project" and i + 1 < len(argv):
                i += 2
                continue
            if tok.startswith("--project="):
                i += 1
                continue
            rest.append(tok)
            i += 1

        if not rest:
            raise CLIError("interactive")  # handled by app entry point

        if rest[0] in ("--help", "-h"):
            return HelpCommand(scope=None)
        if rest[0] == "help":
            return HelpCommand(scope=rest[1] if len(rest) > 1 else None)

        token = rest[0]

        # Slash pseudo-actions parsed for TUI line input reuse.
        if token.startswith("/"):
            if token in ("/help",):
                return HelpCommand(scope=None)
            if token in ("/exit", "/quit"):
                return QuitCommand()
            if token == "/project":
                return ProjectCommand(path=rest[1] if len(rest) > 1 else None)
            if token in ("/hint", "/more", "/solution"):
                return cls._slash_assist(token)
            if token == "/clear":
                return ClearCommand()
            if token == "/practice":
                options, positional = cls._parse_flags(rest[1:])
                return cls._action_command("practice", options, positional)
            if token == "/examples":
                options, positional = cls._parse_flags(rest[1:])
                return cls._action_command("examples", options, positional)
            if token == "/evaluate":
                options, positional = cls._parse_flags(rest[1:])
                return cls._action_command("evaluate", options, positional)
            if token == "/exam-init":
                options, positional = cls._parse_flags(rest[1:])
                return cls._action_command("exam-init", options, positional)
            if token in ("/exam-finish", "/finish-exam"):
                options, positional = cls._parse_flags(rest[1:])
                return cls._action_command("exam-finish", options, positional)
            if token == "/ask":
                return AskCommand(question=" ".join(rest[1:]))
            raise CLIError(f"unknown slash command: {token} (try /help)")

        if token == "config":
            sub = rest[1] if len(rest) > 1 else None
            if sub == "init":
                return HelpCommand(scope="config-init")
            raise CLIError("unknown config command; expected `config init`")

        if token == "student":
            raise CLIError(
                "student identity comes from the name you provide at session "
                "start; there is no /student command"
            )
        if token == "project":
            return ProjectCommand(path=rest[1] if len(rest) > 1 else None)
        if token in ("hint", "more", "solution"):
            return cls._slash_assist("/" + token)
        if token in ("clear",):
            return ClearCommand()
        if token in ("exit", "quit"):
            return QuitCommand()

        if token not in AVAILABLE_ACTIONS:
            raise CLIError(
                f"unknown action: {token!r}; available: {', '.join(AVAILABLE_ACTIONS)}"
            )

        options, positional = cls._parse_flags(rest[1:])

        return cls._action_command(token, options, positional)

    @staticmethod
    def _slash_assist(token: str) -> Command:
        name = token.lstrip("/")
        if name == "hint":
            return HintCommand()
        if name == "solution":
            return SolutionCommand()
        return MoreCommand()

    @classmethod
    def parse_line(cls, line: str) -> Command:
        """Parse a single interactive shell/TUI line (shlex-style splitting)."""
        import shlex

        tokens = shlex.split(line)
        if not tokens:
            raise CLIError("")
        if tokens[0].startswith("/") or tokens[0] in AVAILABLE_ACTIONS:
            return cls.parse_argv(tokens)
        if tokens[0] in ("help", "project", "hint", "more", "solution",
                         "clear", "exit", "quit", "student"):
            return cls.parse_argv(tokens)
        options, positional = cls._parse_flags(tokens[1:])
        return cls._action_command(tokens[0], options, positional)

    @staticmethod
    def command_help() -> str:
        return "\n".join(
            [
                "ADA Sensei commands",
                "",
                "Actions:",
                "  practice [--topic T] [--difficulty D] [--objective O] "
                "[--adaptive/--no-adaptive]",
                "    e.g. practice --topic compose-state --difficulty intermediate",
                "  ask <question>",
                "    e.g. ask why does LazyColumn not update?",
                "  examples <topic>",
                "    e.g. examples ViewModel",
                "  evaluate [--exercise <uri>] [--yes] [--instrumented (future)]",
                "    e.g. evaluate --yes",
                "  exam-init [<statement>] [--yes]",
                "    start an exam from an instructor statement (file, Markdown,",
                "    structured definition, or inline text)",
                "    e.g. exam-init ~/exams/midterm.md --yes",
                "  exam-finish [--yes]",
                "    finish the active exam, score it, and generate the report",
                "    e.g. exam-finish --yes",
                "",
                "Interactive (slash) commands:",
                "  /help                     show this help",
                "  /exit, /quit              leave the session",
                "  /project [<path>]         set / show the active project",
                "    e.g. /project ~/my-project",
                "  /practice [options]       start a practice session",
                "    e.g. /practice --topic state --difficulty intermediate",
                "  /ask <question>           ask a question",
                "    e.g. /ask why does LazyColumn not update?",
                "  /examples <topic>         show a teachable example",
                "    e.g. /examples ViewModel",
                "  /evaluate [--yes]         evaluate the project",
                "    e.g. /evaluate --yes",
                "  /exam-init [<statement>]   start an exam (needs confirmation)",
                "    e.g. /exam-init docs/exam.md",
                "  /exam-finish              finish the active exam",
                "    e.g. /exam-finish",
                "  /hint /more /solution     advance the assistance level",
                "  /clear                    clear the presentation view",
                "",
                "Tips:",
                "  Student identity is set by the name you give at session start; "
                "there is no /student command.",
                "",
                "Meta:",
                "  config init               write the default config template",
                "",
                "Global:",
                "  --project <path>          set the active project before any action",
                "  --yes                     confirm non-interactive Gradle evaluation",
                "  --offline                 avoid network calls",
            ]
        )