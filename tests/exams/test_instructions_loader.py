from __future__ import annotations

import os
from pathlib import Path

import pytest
from ada_sensei.exams.instructions import InstructionsLoader
from ada_sensei.resources.paths import ResourcePathError

EXAMPLE = (
    Path(__file__).parents[2]
    / "specs/007-examine/examples/domino-conquista.exam.v2.json"
)


def _instructions(tmp_path: Path, name: str = "instructions.md") -> Path:
    path = tmp_path / name
    path.write_text(
        "# Exam instructions\n\nImplement the requirements.", encoding="utf-8"
    )
    return path


def test_loads_absolute_instructions(tmp_path):
    path = _instructions(tmp_path)
    document = InstructionsLoader().load(path)
    assert document.path == path.resolve()
    assert document.text.startswith("# Exam instructions")


def test_loads_relative_instructions_from_base(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    path = _instructions(tmp_path / "docs", "instrucciones é.md")
    monkeypatch.chdir(tmp_path)
    document = InstructionsLoader(base_dir=tmp_path).load(
        "docs/instrucciones é.md"
    )
    assert document.path == path.resolve()


def test_loads_tilde_path(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    path = _instructions(home)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    assert InstructionsLoader().load("~/instructions.md").path == path.resolve()


def test_rejects_exam_definition_as_instructions(tmp_path):
    exam = tmp_path / "domino-conquista.exam.json"
    exam.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ResourcePathError) as exc:
        InstructionsLoader().load(exam)

    message = str(exc.value)
    assert "Instructions resource error" in message
    assert "configure it with /instructions <path>" in message
    assert "Resource: instructions" in message


def test_missing_instructions_error(tmp_path):
    with pytest.raises(ResourcePathError) as exc:
        InstructionsLoader(tmp_path).load("absent.md")
    assert "Reason: file does not exist" in str(exc.value)


def test_directory_as_instructions_error(tmp_path):
    with pytest.raises(ResourcePathError) as exc:
        InstructionsLoader(tmp_path).load(tmp_path)
    assert "path is not a regular file" in str(exc.value)


def test_unreadable_instructions_error(tmp_path):
    if os.name == "nt" or hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("permission checks are not meaningful for this user/platform")
    path = _instructions(tmp_path)
    path.chmod(0)
    with pytest.raises(ResourcePathError) as exc:
        InstructionsLoader().load(path)
    assert "permission denied" in str(exc.value)


def test_loads_packaged_instructions():
    document = InstructionsLoader().load_package("en-US")
    assert document.source == "ada_sensei.resources:instructions/default.en.md"
    assert "# Exam instructions" in document.text
