from __future__ import annotations

from ada_sensei.tools.inspector import ProjectInspector


def test_read_only(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "Main.kt").write_text("fun main() {}")
    inspector = ProjectInspector(tmp_path)

    # read-only API surface: no write/delete/modify methods
    write_like = {"write_text", "write_bytes", "mkdir", "unlink", "rename", "replace"}
    methods = {m for m in dir(inspector) if not m.startswith("_")}
    assert not write_like.intersection(methods)

    source = inspector.list_source_files()
    assert any("Main.kt" in f for f in source)
    assert inspector.read_file("app/Main.kt") == "fun main() {}"
    assert inspector.has_gradle_wrapper() is False


def test_structure_and_wrapper(tmp_path):
    (tmp_path / "gradlew").write_text("#!/bin/sh\n")
    (tmp_path / "app" / "src" / "main").mkdir(parents=True)
    (tmp_path / "app" / "src" / "main" / "Main.kt").write_text("")
    inspector = ProjectInspector(tmp_path)
    assert inspector.has_gradle_wrapper()
    assert inspector.structure(suffix=(".kt",))


def test_read_escapes_rejected(tmp_path):
    (tmp_path / "inside.txt").write_text("ok")
    inspector = ProjectInspector(tmp_path)
    try:
        inspector.read_file("../outside.txt")
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")
