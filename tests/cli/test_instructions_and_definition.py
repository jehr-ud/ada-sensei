from __future__ import annotations

import json
from pathlib import Path

from ada_sensei.cli.commands import (
    ExamDefinitionCommand,
    ExamDefinitionResult,
    ExamineStartCommand,
    InstructionsCommand,
    InstructionsResult,
)
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


def _instructions(base: Path, name: str = "instructions.md") -> Path:
    path = base / name
    path.write_text("# Exam instructions\n\nDo the work.", encoding="utf-8")
    return path


def _definition(base: Path, name: str = "exam.json") -> Path:
    path = base / name
    path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def test_instructions_command_loads_markdown(tmp_path):
    router = _router(tmp_path)
    path = _instructions(tmp_path)
    result = router.dispatch(InstructionsCommand(path=str(path)))
    assert isinstance(result, InstructionsResult)
    assert router.context.instructions_path == str(path.resolve())


def test_exam_definition_command_loads_json(tmp_path):
    router = _router(tmp_path)
    path = _definition(tmp_path)
    result = router.dispatch(ExamDefinitionCommand(path=str(path)))
    assert isinstance(result, ExamDefinitionResult)
    assert router.context.exam_definition_path == str(path.resolve())
    assert router.context.instructions_path is None


def test_exam_json_passed_to_instructions_is_rejected(tmp_path):
    router = _router(tmp_path)
    exam = _definition(tmp_path, "domino-conquista.exam.json")
    result = router.dispatch(InstructionsCommand(path=str(exam)))
    assert "Instructions resource error" in result.message
    assert "exam definition JSON cannot be used as instructions" in result.message
    assert router.context.instructions_path is None
    assert router.context.exam_definition_path is None


def test_exam_init_configures_definition_not_instructions(tmp_path):
    router = _router(tmp_path)
    exam = _definition(tmp_path)
    result = router.dispatch(ExamineStartCommand(statement=str(exam)))
    assert "confirmation" in result.message
    assert router.context.exam_definition_path == str(exam.resolve())
    assert router.context.instructions_path is None


def test_relative_paths_ignore_process_cwd(tmp_path, monkeypatch):
    base = tmp_path / "base"
    base.mkdir()
    _instructions(base)
    _definition(base)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    router = _router(tmp_path, base_dir=base)

    assert isinstance(
        router.dispatch(InstructionsCommand(path="instructions.md")),
        InstructionsResult,
    )
    assert isinstance(
        router.dispatch(ExamDefinitionCommand(path="exam.json")),
        ExamDefinitionResult,
    )


def test_parser_exposes_independent_commands(tmp_path):
    instructions = CommandParser.parse_argv(["/instructions", "a.md"])
    definition = CommandParser.parse_argv(["/exam-definition", "b.json"])
    assert isinstance(instructions, InstructionsCommand)
    assert isinstance(definition, ExamDefinitionCommand)


def test_persisted_foreign_absolute_path_is_not_reused(tmp_path):
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

    assert "instructions_wrong_resource" not in status.blockers
    assert (
        "instructions_missing" in status.blockers
        or "instructions_invalid" in status.blockers
    )
    assert status.ready_to_start is False
