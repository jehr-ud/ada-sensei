"""Interactive (legacy) terminal shell dispatching typed commands.

This shell is retained as a lightweight line-oriented fallback and for tests.
The primary interactive experience is the Textual TUI (cli/tui/), but both use
the same CommandRouter (RQ-CLI-004).
"""

from __future__ import annotations

import sys

from .commands import (
    ClearResult,
    Command,
    CommandResult,
    ErrorResponse,
    HelpResult,
    InternalFailure,
    QuitResult,
)
from .config_cmd import ConfigInitCommand
from .errors import CLIError
from .formatter import Formatter
from .parser import CommandParser
from .router import CommandRouter


class Shell:
    """Interactive ADA Sensei shell with slash commands."""

    def __init__(
        self,
        router: CommandRouter,
        inp=None,
        out=None,
        formatter: Formatter | None = None,
    ) -> None:
        self.router = router
        self.inp = inp
        self.out = out or sys.stdout
        self.formatter = formatter or Formatter(router.secrets)
        self.running = True

    def print(self, text: str = "") -> None:
        self.out.write(text + "\n")
        self.out.flush()

    def prompt(self, label: str = "> ") -> str:
        if self.inp is None:
            self.out.write(label)
            self.out.flush()
            line = sys.stdin.readline()
        else:
            line = self.inp.readline()
        if not line:
            raise EOFError
        return line.rstrip("\n")

    def ask_yes_no(self, label: str) -> bool:
        try:
            answer = self.prompt(label).strip().lower()
        except EOFError:
            return False
        return answer in {"y", "yes"}

    def run(self, prompt_label: str = "> ") -> None:
        self.print("ADA Sensei. Type /help for commands, /exit to leave.")
        while self.running:
            try:
                line = self.prompt(prompt_label)
            except EOFError:
                self.print("/exit")
                break
            if not line or not line.strip():
                continue
            try:
                self.execute_line(line)
            except EOFError:
                break
            except CLIError as exc:
                if str(exc):
                    self.print("Error: " + self.formatter.error(str(exc)))
            except Exception as exc:
                self.print("Error: " + self.formatter.sanitized(exc))

    def execute_line(self, line: str) -> None:
        command = CommandParser.parse_line(line)
        self.dispatch(command)

    def dispatch(self, command: Command) -> None:
        if self._is_config_init(command):
            path = ConfigInitCommand.config_init(env=self.router.env)
            self.print(f"Wrote default config template to {path}")
            self.print(ConfigInitCommand.env_override_docs())
            return

        result = self.router.dispatch(command)
        self._render(result)

    def _render(self, result: CommandResult) -> None:
        if isinstance(result, QuitResult):
            self.running = False
            return
        if isinstance(result, ErrorResponse):
            self.print("Error: " + self.formatter.error(result.message))
            return
        if isinstance(result, InternalFailure):
            self.print("Error: " + self.formatter.error(result.message))
            return
        if isinstance(result, ClearResult):
            self.print("")
            return
        if isinstance(result, HelpResult):
            self.print(result.text)
            return
        text = self.formatter.result(result)
        if text:
            self.print(text)
        notice = self.router.context_notice()
        if notice:
            self.print("Note: " + self.formatter.error(notice))

    @staticmethod
    def _is_config_init(command: Command) -> bool:
        from .commands import HelpCommand

        return isinstance(command, HelpCommand) and command.scope == "config-init"


__all__ = ["Shell"]
