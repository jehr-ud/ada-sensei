from __future__ import annotations

from ada_sensei.actions.evaluate import StaticAnalysisTool
from ada_sensei.evaluation import EVALUATE_RUBRIC, RubricEngine
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


def test_lint_detekt_report(tmp_path):
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
            {"severity": "info", "message": "Missing baseline", "file": "Main.kt"},
        ],
    )
    Fixture.write_detekt_report(
        proj,
        [
            {"severity": "warning", "message": "ComplexMethod", "line": "12"},
            {"severity": "error", "message": "TooManyFunctions", "line": "30"},
            {"severity": "info", "message": "MagicNumber", "line": "44"},
        ],
    )
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_all()
    severities = {e.severity for e in evidence if e.source == "lint" and e.severity}
    detekt_severities = {
        e.severity for e in evidence if e.source == "detekt" and e.severity
    }
    # RQ-EVA-015: severity is preserved, not flattened.
    assert severities == {"error", "warning", "info"}
    assert detekt_severities == {"error", "warning", "info"}
    assert any(e.status == "fail" for e in evidence if e.severity == "error")


def test_detekt_warn_severity(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_detekt_report(
        proj,
        [{"severity": "warning", "message": "ComplexMethod", "line": "12"}],
    )
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_detekt()
    warnings = [
        e for e in evidence if e.source == "detekt" and e.severity == "warning"
    ]
    assert warnings


def test_findings_feed_the_rubric_not_one_to_one_deductions(tmp_path):
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
    engine = RubricEngine(EVALUATE_RUBRIC)
    assert engine.scorer.score("android_practices", lint) == (3, None)
    assert engine.scorer.score("code_quality", detekt) == (3, None)


def test_error_findings_lower_the_dimension_score(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_lint_report(
        proj, [{"severity": "error", "message": "bad", "file": "M.kt"}]
    )
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_lint()
    engine = RubricEngine(EVALUATE_RUBRIC)
    assert engine.scorer.score("android_practices", evidence) == (1, None)


def test_no_reports_limitation(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner()
    evidence = StaticAnalysisTool(str(proj), runner=runner).run_all()
    assert any(e.source == "lint" for e in evidence)
    assert any(e.source == "detekt" for e in evidence)
    assert any(e.status == "pass" for e in evidence if e.source == "lint")


def test_missing_wrapper_is_a_limitation_not_a_pass(tmp_path):
    proj = tmp_path / "no-wrapper"
    proj.mkdir()
    evidence = StaticAnalysisTool(str(proj), runner=StubRunner()).run_all()
    assert all(e.status == "missing" for e in evidence)
    assert all("limitation" in e.message.lower() for e in evidence)
