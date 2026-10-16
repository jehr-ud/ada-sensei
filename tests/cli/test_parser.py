from __future__ import annotations

import pytest
from ada_sensei.cli.commands import (
    AskCommand,
    ClearCommand,
    DiagnoseCommand,
    EvaluateCommand,
    ExamineFinishCommand,
    ExamineStartCommand,
    ExamplesCommand,
    HelpCommand,
    HintCommand,
    LanguageCommand,
    LearnCommand,
    MoreCommand,
    PracticeCommand,
    ProjectCommand,
    QuitCommand,
    SolutionCommand,
)
from ada_sensei.cli.errors import CLIError
from ada_sensei.cli.parser import AVAILABLE_ACTIONS, CommandParser


def test_practice_options():
    cmd = CommandParser.parse_argv(
        [
            "practice",
            "--topic",
            "compose-state",
            "--difficulty",
            "intermediate",
            "--objective",
            "list",
        ]
    )
    assert isinstance(cmd, PracticeCommand)
    assert cmd.topic == "compose-state"
    assert cmd.difficulty == "intermediate"
    assert cmd.objective == "list"
    assert cmd.adaptive is True


def test_adaptive_flag():
    assert CommandParser.parse_argv(["practice", "--no-adaptive"]).adaptive is False
    assert CommandParser.parse_argv(["practice"]).adaptive is True


def test_instrumented_reserved():
    cmd = CommandParser.parse_argv(["evaluate", "--instrumented"])
    assert isinstance(cmd, EvaluateCommand)
    assert cmd.instrumented is True


def test_known_actions():
    for action in AVAILABLE_ACTIONS:
        cmd = CommandParser.parse_argv([action])
        assert isinstance(cmd, (PracticeCommand, AskCommand, ExamplesCommand,
                                EvaluateCommand, ExamineStartCommand,
                                ExamineFinishCommand, LanguageCommand,
                                LearnCommand, DiagnoseCommand))


def test_exam_init_parses():
    cmd = CommandParser.parse_argv(["exam-init", "~/exams/midterm.md", "--yes"])
    assert isinstance(cmd, ExamineStartCommand)
    assert cmd.statement == "~/exams/midterm.md"
    assert cmd.confirmed is True


def test_exam_finish_slash():
    cmd = CommandParser.parse_argv(["/exam-finish"])
    assert isinstance(cmd, ExamineFinishCommand)
    assert cmd.confirmed is False
    finish = CommandParser.parse_argv(["/finish-exam", "--yes"])
    assert isinstance(finish, ExamineFinishCommand)
    assert finish.confirmed is True


def test_unknown_action_error():
    with pytest.raises(CLIError):
        CommandParser.parse_argv(["frobnicate"])


def test_evaluate_exercise_flag():
    cmd = CommandParser.parse_argv(["evaluate", "--exercise", "exercise://e1"])
    assert isinstance(cmd, EvaluateCommand)
    assert cmd.exercise_id == "exercise://e1"


def test_config_init_action():
    cmd = CommandParser.parse_argv(["config", "init"])
    assert isinstance(cmd, HelpCommand)
    assert cmd.scope == "config-init"


def test_ask_question_text():
    cmd = CommandParser.parse_argv(["ask", "explain", "MVVM", "state"])
    assert isinstance(cmd, AskCommand)
    assert cmd.question == "explain MVVM state"


def test_slash_student_rejected():
    with pytest.raises(CLIError):
        CommandParser.parse_argv(["/student", "student://bob"])
    with pytest.raises(CLIError):
        CommandParser.parse_argv(["student", "bob"])


def test_help_includes_examples():
    help_text = CommandParser.command_help()
    assert "practice --topic compose-state --difficulty intermediate" in help_text
    assert "ask why does LazyColumn not update?" in help_text
    assert "examples ViewModel" in help_text
    assert "evaluate --yes" in help_text


def test_slash_assistance():
    assert isinstance(CommandParser.parse_argv(["/hint"]), HintCommand)
    assert isinstance(CommandParser.parse_argv(["/more"]), MoreCommand)
    assert isinstance(CommandParser.parse_argv(["/solution"]), SolutionCommand)


def test_slash_help_exit_clear():
    assert isinstance(CommandParser.parse_argv(["/help"]), HelpCommand)
    assert isinstance(CommandParser.parse_argv(["/quit"]), QuitCommand)
    assert isinstance(CommandParser.parse_argv(["/clear"]), ClearCommand)


def test_slash_project():
    cmd = CommandParser.parse_argv(["/project", "/some/path"])
    assert isinstance(cmd, ProjectCommand)
    assert cmd.path == "/some/path"


def test_project_direct():
    cmd = CommandParser.parse_argv(["project"])
    assert isinstance(cmd, ProjectCommand)
    assert cmd.path is None


def test_slash_unknown_error():
    with pytest.raises(CLIError):
        CommandParser.parse_argv(["/bogus"])
