from __future__ import annotations

from ada_sensei.actions.evaluate import Rubric, StaticAnalysisTool
from helpers import Fixture


class StubRunner:
    def run(self, cmd, *, cwd=None, timeout=None):
        from ada_sensei.tools.subprocess import SubprocessResult

        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_s=0.1,
        )


def test_lint_report_errors(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_lint_report(
        proj,
        [
            {"severity": "error", "message": "Hardcoded string", "file": "Main.kt"},
            {
                "severity": "warning",
                "message": "ObsoleteLayoutParam",
                "file": "Main.kt",
            },
        ],
    )
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_lint()
    errors = [e for e in evidence if e.source == "lint" and e.severity == "error"]
    assert errors
    assert any(e.status == "fail" for e in errors)


def test_detekt_warn_severity(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_detekt_report(
        proj,
        [
            {"severity": "warning", "message": "ComplexMethod", "line": "12"},
        ],
    )
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_detekt()
    warnings = [e for e in evidence if e.source == "detekt" and e.severity == "warning"]
    assert warnings


def test_static_scores_static_code_quality(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_detekt_report(
        proj, [{"severity": "warning", "message": "x", "line": "1"}]
    )
    Fixture.write_lint_report(
        proj, [{"severity": "info", "message": "namespace", "file": "M.kt"}]
    )
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_all()
    lint = [e for e in evidence if e.source == "lint"]
    detekt = [e for e in evidence if e.source == "detekt"]
    assert Rubric.dimension_score("android_practices", lint) == 3
    assert Rubric.dimension_score("code_quality", detekt) == 3


def test_no_reports_limitation(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner()
    evidence = StaticAnalysisTool(str(proj), runner=runner).run_all()
    assert any(e.source == "lint" for e in evidence)
    assert any(e.source == "detekt" for e in evidence)
    assert any(e.status == "pass" for e in evidence if e.source == "lint")