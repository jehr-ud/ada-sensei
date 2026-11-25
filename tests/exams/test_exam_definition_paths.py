from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from ada_sensei.exams.definition import ExamDefinitionLoader
from ada_sensei.exams.models import ExamDefinitionError

EXAMPLE = (
    Path(__file__).parents[2]
    / "specs/007-examine/examples/domino-conquista.exam.v2.json"
)


def _definition(tmp_path: Path, name: str = "exam.json") -> Path:
    path = tmp_path / name
    path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def test_loads_absolute_definition(tmp_path):
    path = _definition(tmp_path)
    definition = ExamDefinitionLoader().load(path)
    assert definition.exam_id == "domino-conquista"


def test_loads_relative_definition_from_base(tmp_path, monkeypatch):
    (tmp_path / "exams").mkdir()
    path = _definition(tmp_path / "exams", "examen é.json")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    definition = ExamDefinitionLoader().load(
        "../exams/examen é.json", base_dir=elsewhere
    )

    assert definition.exam_id == "domino-conquista"
    assert path.exists()


def test_missing_definition_error(tmp_path):
    with pytest.raises(ExamDefinitionError) as exc:
        ExamDefinitionLoader().load(tmp_path / "absent.json", base_dir=tmp_path)
    assert "file does not exist" in str(exc.value)


def test_directory_as_definition_error(tmp_path):
    with pytest.raises(ExamDefinitionError) as exc:
        ExamDefinitionLoader().load(tmp_path, base_dir=tmp_path)
    assert "path is not a regular file" in str(exc.value)


def test_unreadable_definition_error(tmp_path):
    if os.name == "nt" or hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("permission checks are not meaningful for this user/platform")
    path = _definition(tmp_path)
    path.chmod(0)
    with pytest.raises(ExamDefinitionError) as exc:
        ExamDefinitionLoader().load(path)
    assert "permission denied" in str(exc.value)


def test_invalid_schema_reports_pointer(tmp_path):
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    del payload["rubric_ref"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ExamDefinitionError) as exc:
        ExamDefinitionLoader().load(path)
    assert "/rubric_ref" in str(exc.value)
    assert "Exam definition error" not in str(exc.value)


def test_instructions_extension_is_rejected(tmp_path):
    path = tmp_path / "instructions.md"
    path.write_text("# Exam", encoding="utf-8")
    with pytest.raises(ExamDefinitionError) as exc:
        ExamDefinitionLoader().load(path)
    assert "only .json exam definitions are accepted" in str(exc.value)


def test_foreign_absolute_definition_is_rejected(tmp_path):
    with pytest.raises(ExamDefinitionError) as exc:
        ExamDefinitionLoader().load("C:\\exams\\exam.json", base_dir=tmp_path)
    assert "another operating system's absolute format" in str(exc.value)
