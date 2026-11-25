from __future__ import annotations

import os

import pytest
from ada_sensei.resources.paths import (
    ResourceKind,
    ResourcePathError,
    ResourceReference,
    ResourceResolver,
)


def test_absolute_path_is_respected(tmp_path):
    target = tmp_path / "exam.json"
    target.write_text("{}", encoding="utf-8")
    resolved = ResourceResolver(tmp_path).resolve(
        target, ResourceKind.EXAM_DEFINITION
    )
    assert resolved == target.resolve()


def test_relative_path_uses_explicit_base_not_cwd(tmp_path, monkeypatch):
    base = tmp_path / "base"
    docs = base / "docs"
    docs.mkdir(parents=True)
    target = docs / "instructions with spaces.md"
    target.write_text("# Exam", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    resolved = ResourceResolver(base).resolve(
        "docs/instructions with spaces.md", ResourceKind.INSTRUCTIONS
    )

    assert resolved == target


def test_unicode_and_tilde_paths(tmp_path, monkeypatch):
    home = tmp_path / "home"
    exams = home / "exámenes"
    exams.mkdir(parents=True)
    target = exams / "instrucciones_ñ.md"
    target.write_text("# Examen", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    resolved = ResourceResolver(tmp_path).resolve(
        "~/exámenes/instrucciones_ñ.md", ResourceKind.INSTRUCTIONS
    )

    assert resolved == target


def test_missing_file_reports_resource_and_resolved_path(tmp_path):
    with pytest.raises(ResourcePathError) as exc:
        ResourceResolver(tmp_path).resolve("absent.json", ResourceKind.EXAM_DEFINITION)

    message = str(exc.value)
    assert "Exam definition error" in message
    assert "Resource: exam_definition" in message
    assert str(tmp_path / "absent.json") in message
    assert "Reason: file does not exist" in message


def test_directory_is_rejected_as_file(tmp_path):
    (tmp_path / "folder").mkdir()
    with pytest.raises(ResourcePathError) as exc:
        ResourceResolver(tmp_path).resolve("folder", ResourceKind.INSTRUCTIONS)
    assert "path is not a regular file" in str(exc.value)


def test_unreadable_file_is_reported(tmp_path):
    if os.name == "nt" or hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("permission checks are not meaningful for this user/platform")
    target = tmp_path / "instructions.md"
    target.write_text("# Exam", encoding="utf-8")
    target.chmod(0)

    with pytest.raises(ResourcePathError) as exc:
        ResourceResolver(tmp_path).resolve(target, ResourceKind.INSTRUCTIONS)
    assert "Reason: permission denied" in str(exc.value)


def test_foreign_absolute_path_is_rejected(tmp_path):
    with pytest.raises(ResourcePathError) as exc:
        ResourceResolver(tmp_path).resolve(
            "C:\\exams\\exam.json", ResourceKind.EXAM_DEFINITION
        )
    assert "another operating system's absolute format" in str(exc.value)


def test_saved_base_from_another_system_is_not_silently_reused(tmp_path):
    reference = ResourceReference(
        value="exams/exam.json", base=str(tmp_path / "old-system")
    )

    with pytest.raises(ResourcePathError) as exc:
        ResourceResolver(tmp_path).resolve_reference(
            reference, ResourceKind.EXAM_DEFINITION
        )

    assert "saved base directory is not available" in str(exc.value)
