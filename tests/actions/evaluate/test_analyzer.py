from __future__ import annotations

from ada_sensei.actions.evaluate import AndroidProjectAnalyzer
from helpers import Fixture


def test_active_project(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    analyzer = AndroidProjectAnalyzer(proj)
    assert analyzer.project_path == proj.resolve()


def test_structure_inspected(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    evidence = AndroidProjectAnalyzer(proj).analyze()
    assert evidence
    assert any(e.type == "structure" for e in evidence)
    assert any(e.status == "pass" for e in evidence)


def test_missing_manifest_reported_missing(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    (proj / "app" / "src" / "main" / "AndroidManifest.xml").unlink()
    evidence = AndroidProjectAnalyzer(proj).analyze()
    manifest = next(e for e in evidence if e.file == "app/src/main/AndroidManifest.xml")
    assert manifest.status == "missing"