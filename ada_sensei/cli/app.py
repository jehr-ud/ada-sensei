"""Direct CLI/application entry point (RQ-CLI-001).

``CLIApp.main`` starts the Textual TUI when no action is given, otherwise parses
argv into a typed command, dispatches it through the shared
:class:`CommandRouter`, and exits with code ``0`` (success), ``1`` (expected
user error), or ``2`` (unexpected internal failure) per RQ-CLI-018.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from .commands import (
    Command,
    CommandResult,
    ErrorResponse,
    HelpCommand,
    InternalFailure,
    QuitCommand,
)
from .errors import CLIError
from .formatter import Formatter
from .router import CommandRouter

EXIT_OK = 0
EXIT_USER_ERROR = 1
EXIT_INTERNAL = 2


class CLIApp:
    @staticmethod
    def _extract_globals(argv: list[str]) -> tuple[list[str], str | None]:
        """Pull `--project <path>` (and future globals) out of argv."""
        rest: list[str] = []
        project: str | None = None
        i = 0
        while i < len(argv):
            tok = argv[i]
            if tok == "--project" and i + 1 < len(argv):
                project = argv[i + 1]
                i += 2
                continue
            if tok.startswith("--project="):
                project = tok.split("=", 1)[1]
                i += 1
                continue
            rest.append(tok)
            i += 1
        return rest, project

    @staticmethod
    def parse_command(argv: list[str]) -> Command:
        from .parser import CommandParser

        if not argv:
            raise CLIError("missing action; try `ada-sensei --help`")
        return CommandParser.parse_argv(argv)

    @staticmethod
    def _emit_result(
        router: CommandRouter, formatter: Formatter, result: CommandResult
    ) -> int:
        if isinstance(result, ErrorResponse):
            sys.stderr.write(f"ada-sensei: {formatter.error(result.message)}\n")
            return EXIT_USER_ERROR
        if isinstance(result, InternalFailure):
            sys.stderr.write(f"ada-sensei: {formatter.error(result.message)}\n")
            return EXIT_INTERNAL
        rendered = formatter.result(result)
        if rendered:
            sys.stdout.write(rendered + "\n")
        notice = router.context_notice()
        if notice:
            sys.stderr.write(f"\nNote: {formatter.error(notice)}\n")
        return EXIT_OK

    @staticmethod
    def _run_tui(router: CommandRouter, formatter: Formatter) -> int:
        try:
            from .tui.app import AdaSenseiTUI

            app = AdaSenseiTUI(router=router, formatter=formatter)
            app.run()
        except KeyboardInterrupt:
            return EXIT_OK
        except Exception as exc:
            sys.stderr.write(f"ada-sensei: {formatter.sanitized(exc)}\n")
            return EXIT_INTERNAL
        return EXIT_OK

    @classmethod
    def run(
        cls,
        argv: Sequence[str] | None = None,
        *,
        router: CommandRouter | None = None,
    ) -> int:
        argv = list(sys.argv[1:] if argv is None else argv)

        router = router or CommandRouter()
        formatter = Formatter(router.secrets)

        if not argv:
            return cls._run_tui(router, formatter)

        rest, project = cls._extract_globals(argv)
        if project:
            router.context.set_project(project)

        try:
            command: Command = cls.parse_command(rest)
        except CLIError as exc:
            if str(exc):
                sys.stderr.write(f"ada-sensei: {formatter.error(str(exc))}\n")
            return EXIT_USER_ERROR

        if isinstance(command, HelpCommand):
            from .parser import CommandParser

            sys.stdout.write(CommandParser.command_help() + "\n")
            return EXIT_OK
        if isinstance(command, QuitCommand):
            return EXIT_OK

        result = router.dispatch(command)
        return cls._emit_result(router, formatter, result)

    @staticmethod
    def main() -> None:
        """Console-script entry point; exits with the computed status code."""
        sys.exit(CLIApp.run())


if __name__ == "__main__":
    CLIApp.main()