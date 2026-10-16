"""Centralized action registry (RQ-TUI-035, RQ-CLI-032).

Single source of truth: every student-facing action appears once, builds the
same typed command as the CLI parser, and carries es-CO/en-US labels.
"""

from __future__ import annotations

from ada_sensei.cli import action_registry as reg
from ada_sensei.cli.commands import (
    AskCommand,
    DiagnoseCommand,
    EvaluateCommand,
    ExamineFinishCommand,
    ExamineStartCommand,
    ExamplesCommand,
    HelpCommand,
    LanguageCommand,
    LearnCommand,
    PracticeCommand,
)
from ada_sensei.cli.parser import AVAILABLE_ACTIONS, CommandParser


def test_all_student_actions_registered_once():
    actions = reg.get_actions()
    ids = [a.id for a in actions]
    assert ids == [
        "ask",
        "practice",
        "examples",
        "evaluate",
        "exam-init",
        "exam-finish",
        "learn",
        "diagnose",
        "language",
        "help",
    ]
    assert len(set(ids)) == len(ids)


def test_registry_matches_parser_actions():
    assert set(reg.action_ids()) >= set(AVAILABLE_ACTIONS)
    assert set(AVAILABLE_ACTIONS) >= {
        "practice",
        "ask",
        "examples",
        "evaluate",
        "exam-init",
        "exam-finish",
        "language",
        "learn",
        "diagnose",
    }


def test_each_action_builds_correct_command():
    assert isinstance(reg.build_command("ask", "why?"), AskCommand)
    assert isinstance(reg.build_command("practice", "t"), PracticeCommand)
    assert isinstance(reg.build_command("examples", "V"), ExamplesCommand)
    assert isinstance(reg.build_command("evaluate", ""), EvaluateCommand)
    assert isinstance(reg.build_command("exam-init", "s"), ExamineStartCommand)
    assert isinstance(reg.build_command("exam-finish", ""), ExamineFinishCommand)
    assert isinstance(reg.build_command("learn", ""), LearnCommand)
    assert isinstance(reg.build_command("diagnose", ""), DiagnoseCommand)
    assert isinstance(reg.build_command("language", "es-CO"), LanguageCommand)
    assert isinstance(reg.build_command("help", ""), HelpCommand)


def test_registry_commands_match_slash_parsing():
    assert type(reg.build_command("ask", "q?")) is type(
        CommandParser.parse_line("/ask q?")
    )
    assert type(reg.build_command("practice", "")) is type(
        CommandParser.parse_line("/practice")
    )
    assert type(reg.build_command("learn", "")) is type(
        CommandParser.parse_line("/learn")
    )
    assert type(reg.build_command("diagnose", "")) is type(
        CommandParser.parse_line("/diagnose")
    )
    assert type(reg.build_command("language", "es-CO")) is type(
        CommandParser.parse_line("/language es-CO")
    )


def test_spanish_and_english_labels():
    for action in reg.get_actions():
        es = action.label("es-CO")
        en = action.label("en-US")
        assert es and en
        assert action.description("es-CO") and action.description("en-US")
        assert action.hint("es-CO") and action.hint("en-US")
    ask = reg.get_action("ask")
    assert ask is not None
    assert ask.label("es-CO") == "Preguntar"
    assert ask.label("en-US") == "Ask"
    assert reg.get_action("ask").id == "ask"  # stable id untranslated


def test_availability_explains_prerequisites():
    ok, reason = reg.check_availability("evaluate", project_path=None)
    assert not ok and "project" in reason.lower() or "proyecto" in reason.lower()
    ok, _ = reg.check_availability(
        "evaluate", project_path="/tmp/proj", locale="en-US"
    )
    assert ok
    ok, reason = reg.check_availability(
        "exam-finish", project_path="/tmp/p", exam_active=False, locale="en-US"
    )
    assert not ok and reason
    ok, _ = reg.check_availability(
        "exam-finish", project_path="/tmp/p", exam_active=True, locale="es-CO"
    )
    assert ok
