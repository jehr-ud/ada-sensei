from __future__ import annotations

import json
from pathlib import Path

from ada_sensei.context import SessionContext
from ada_sensei.resources.paths import ResourceReference

EXAMPLE = (
    Path(__file__).parents[2]
    / "specs/007-examine/examples/domino-conquista.exam.v2.json"
)


def test_persists_relative_reference_with_base(tmp_path):
    base = tmp_path / "base"
    (base / "exams").mkdir(parents=True)
    exam = base / "exams" / "exam.json"
    exam.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    context = SessionContext(data_dir=tmp_path / "data", base_dir=base)
    context.set_exam_definition("exams/exam.json")
    context.persist()

    saved = json.loads(
        (tmp_path / "data" / "sessions" / "anonymous.json").read_text(encoding="utf-8")
    )
    reference = saved["exam_definition_path"]
    assert reference["value"] == "exams/exam.json"
    assert reference["base"] == str(base)

    restored = SessionContext(data_dir=tmp_path / "data", base_dir=tmp_path)
    restored.state = restored._load_state() or restored.state
    assert restored.exam_definition_path == str(exam.resolve())


def test_legacy_exam_definition_is_migrated(tmp_path):
    exam = tmp_path / "exam.json"
    exam.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "s1.json").write_text(
        json.dumps({"student_id": "student://s1", "instructions_path": str(exam)}),
        encoding="utf-8",
    )

    context = SessionContext(data_dir=tmp_path)
    context.set_student("student://s1")

    assert context.exam_definition_path == str(exam.resolve())
    assert context.instructions_path is None
    assert context.migrated_resources == ("instructions_path -> exam_definition_path",)


def test_invalid_legacy_path_is_not_converted_to_instructions(tmp_path):
    absent = tmp_path / "missing.json"
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "s1.json").write_text(
        json.dumps({"student_id": "student://s1", "instructions_path": str(absent)}),
        encoding="utf-8",
    )

    context = SessionContext(data_dir=tmp_path)
    context.set_student("student://s1")

    assert context.exam_definition_path is None
    assert context.instructions_path == str(absent)
    assert context.migrated_resources == ()


def test_reference_type_is_preserved(tmp_path):
    reference = ResourceReference(
        package="ada_sensei.resources", resource="instructions/default.en.md"
    )
    context = SessionContext(data_dir=tmp_path)
    context.state.instructions_path = reference
    assert "default.en.md" in (context.instructions_path or "")
