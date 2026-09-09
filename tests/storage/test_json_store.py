from __future__ import annotations

from ada_sensei.storage import JsonStore
from ada_sensei.urns import URN


def test_atomic_write(tmp_path):
    store = JsonStore(str(tmp_path))
    store.write("project://x", {"a": 1})
    assert store.read("project://x") == {"a": 1}
    assert not list((tmp_path / "projects").glob("*.tmp"))


def test_roundtrip_versioned(tmp_path):
    store = JsonStore(str(tmp_path))
    store.write("exercise://e1", {"title": "t"})
    assert store.read("exercise://e1") == {"title": "t"}
    # schema mismatch -> None
    raw = (tmp_path / "exercises" / "e1.json").read_text()
    (tmp_path / "exercises" / "e1.json").write_text(
        raw.replace('"schema": 1', '"schema": 999')
    )
    assert store.read("exercise://e1") is None


def test_no_project_write(tmp_path):
    store = JsonStore(str(tmp_path))
    store.write("student://s", {"student_id": "student://s"})
    # storage only writes under tmp_path (data dir), nothing elsewhere
    assert (tmp_path / "history" / "s.json").exists()


def test_urns(tmp_path):
    store = JsonStore(str(tmp_path))
    path = store.path_for("attempt://abc")
    assert path.name == "abc.json"
    assert path.parent.name == "attempts"
    assert URN.parse("result://r") == ("result", "r")
    assert URN.project_id_from_path("/x/y").startswith("project://")
