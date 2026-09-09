from __future__ import annotations

from ada_sensei.actions.evaluate import TestTool as UnitTestTool
from helpers import Fixture


class StubRunner:
    def __init__(self, exit_code=0):
        self.exit_code = exit_code
        self.calls = []

    def run(self, cmd, *, cwd=None, timeout=None):
        self.calls.append((cmd, str(cwd)))
        from ada_sensei.tools.subprocess import SubprocessResult

        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=self.exit_code,
            stdout="tests ran",
            stderr="",
            duration_s=0.1,
        )


def test_reports_collected(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_test_report(proj, tests=5, failures=0)
    runner = StubRunner()
    evidence = UnitTestTool(str(proj), runner=runner).run_unit_tests()
    assert any(e.type == "unit_test" for e in evidence)
    assert any(e.status == "pass" for e in evidence)
    assert runner.calls[0][0][-1] == "testDebugUnitTest"


def test_failing_tests_reported(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_test_report(proj, name="BrokenTest", tests=2, failures=1)
    runner = StubRunner(exit_code=1)
    evidence = UnitTestTool(str(proj), runner=runner).run_unit_tests()
    statuses = [e.status for e in evidence if e.type == "unit_test"]
    assert "fail" in statuses


def test_no_tests_limitation(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner(exit_code=1)
    evidence = UnitTestTool(str(proj), runner=runner).run_unit_tests()
    assert any(e.status in {"fail", "missing"} for e in evidence)