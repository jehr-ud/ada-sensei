from __future__ import annotations

import json
from pathlib import Path

import pytest
from ada_sensei.cli.commands import (
    ExamineStartCommand,
    InstructionsCommand,
    InstructionsResult,
)
from ada_sensei.cli.errors import CLIError
from ada_sensei.cli.parser import CommandParser
from ada_sensei.cli.router import Router
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient

EXAMPLE = (
    Path(__file__).parents[2]
    / "specs/007-examine/examples/domino-conquista.exam.v2.json"
)


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return "{}"


def _router(tmp_path: Path, *, base_dir: Path | None = None) -> Router:
    config = Config(project={"path": str(tmp_path / "project")})
    config.data_dir = tmp_path / "data"
    config.cache_dir = tmp_path / "cache"
    config.base_dir = base_dir or tmp_path
    return Router(config=config, client=FakeClient())


def _definition(base: Path, name: str = "exam.json") -> Path:
    path = base / name
    path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def test_instructions_command_loads_json(tmp_path):
    router = _router(tmp_path)
    path = _definition(tmp_path, "domino-conquista.exam.json")

    result = router.dispatch(InstructionsCommand(path=str(path)))

    assert isinstance(result, InstructionsResult)
    assert router.context.exam_definition_path == str(path.resolve())
    assert router.context.instructions_path is None


def test_instructions_command_shows_configured_json(tmp_path):
    router = _router(tmp_path)
    path = _definition(tmp_path)
    router.dispatch(InstructionsCommand(path=str(path)))

    result = router.dispatch(InstructionsCommand())

    assert isinstance(result, InstructionsResult)
    assert result.path == str(path.resolve())


def test_instructions_command_rejects_markdown(tmp_path):
    router = _router(tmp_path)
    path = tmp_path / "instructions.md"
    path.write_text("# Exam instructions\n\nDo the work.", encoding="utf-8")

    result = router.dispatch(InstructionsCommand(path=str(path)))

    assert "Instructions error" in result.message
    assert "only .json exam definitions are accepted" in result.message
    assert router.context.exam_definition_path is None


def test_exam_init_configures_same_definition(tmp_path):
    router = _router(tmp_path)
    exam = _definition(tmp_path)

    result = router.dispatch(ExamineStartCommand(statement=str(exam)))

    assert "confirmation" in result.message
    assert router.context.exam_definition_path == str(exam.resolve())
    assert router.context.instructions_path is None


def test_relative_path_ignores_process_cwd(tmp_path, monkeypatch):
    base = tmp_path / "base"
    base.mkdir()
    _definition(base)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    router = _router(tmp_path, base_dir=base)

    result = router.dispatch(InstructionsCommand(path="exam.json"))

    assert isinstance(result, InstructionsResult)
    assert router.context.exam_definition_path == str((base / "exam.json").resolve())


def test_parser_exposes_only_instructions_command():
    instructions = CommandParser.parse_argv(["/instructions", "a.json"])

    assert isinstance(instructions, InstructionsCommand)
    with pytest.raises(CLIError):
        CommandParser.parse_argv(["/exam-definition", "b.json"])


def test_persisted_foreign_legacy_path_is_ignored(tmp_path):
    data_dir = tmp_path / "data"
    sessions = data_dir / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "s1.json").write_text(
        json.dumps(
            {
                "student_id": "student://s1",
                "instructions_path": "C:\\exams\\instructions.md",
                "exam_definition_path": None,
            }
        ),
        encoding="utf-8",
    )
    router = _router(tmp_path)
    router.context.set_student("student://s1")

    status = router.exam_preparation_status()

    assert status.instruction_blockers == ()
    assert "no_exam_definition" in status.blockers
    assert status.ready_to_start is False
