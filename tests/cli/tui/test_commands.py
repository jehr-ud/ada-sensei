"""TUI slash commands parse to the same typed command objects as the CLI.

RQ-TUI-003 / RQ-TUI-005 / RQ-TUI-006.
"""

from __future__ import annotations

import pytest
from ada_sensei.cli.commands import (
    AskCommand,
    ClearCommand,
    EvaluateCommand,
    ExamplesCommand,
    HelpCommand,
    HintCommand,
    MoreCommand,
    PracticeCommand,
    QuitCommand,
    SolutionCommand,
)
from ada_sensei.cli.errors import CLIError
from ada_sensei.cli.parser import CommandParser


def test_slash_practice():
    assert isinstance(CommandParser.parse_line("/practice"), PracticeCommand)


def test_slash_ask():
    cmd = CommandParser.parse_line("/ask what is a composable?")
    assert isinstance(cmd, AskCommand)
    assert "composable" in cmd.question


def test_slash_examples():
    cmd = CommandParser.parse_line("/examples mvvm")
    assert isinstance(cmd, ExamplesCommand)
    assert cmd.topic == "mvvm"


def test_slash_evaluate():
    assert isinstance(CommandParser.parse_line("/evaluate"), EvaluateCommand)


def test_slash_student_rejected():
    with pytest.raises(CLIError):
        CommandParser.parse_line("/student alice")


def test_slash_assistance_commands():
    assert isinstance(CommandParser.parse_line("/hint"), HintCommand)
    assert isinstance(CommandParser.parse_line("/more"), MoreCommand)
    assert isinstance(CommandParser.parse_line("/solution"), SolutionCommand)


def test_slash_clear_and_quit():
    assert isinstance(CommandParser.parse_line("/clear"), ClearCommand)
    assert isinstance(CommandParser.parse_line("/quit"), QuitCommand)


def test_help_command():
    assert isinstance(CommandParser.parse_line("/help"), HelpCommand)


def test_unknown_slash_errors():
    with pytest.raises(CLIError):
        CommandParser.parse_line("/bogus")
