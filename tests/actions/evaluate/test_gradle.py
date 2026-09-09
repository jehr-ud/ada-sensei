from __future__ import annotations

from ada_sensei.actions.evaluate import GradleTool
from ada_sensei.tools.subprocess import SubprocessRunner
from helpers import Fixture


class StubRunner:
    def __init__(self, exit_code=0, timed_out=False):
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.calls = []

    def run(self, cmd, *, cwd=None, timeout=None):
        self.calls.append((cmd, str(cwd)))
        from ada_sensei.tools.subprocess import SubprocessResult

        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=None if self.timed_out else self.exit_code,
            stdout="build output",
            stderr="",
            duration_s=0.1,
            timed_out=self.timed_out,
        )


def test_build_attempted(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner(exit_code=0)
    evidence = GradleTool(str(proj), runner=runner).build()
    assert evidence.status == "pass"
    assert evidence.type == "compilation"
    assert runner.calls[-1][0][-1] == "assembleDebug"


def test_build_failure_status(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner(exit_code=1)
    evidence = GradleTool(str(proj), runner=runner).build()
    assert evidence.status == "fail"


def test_timeout_is_limitation(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    runner = StubRunner(timed_out=True)
    evidence = GradleTool(str(proj), runner=runner).build()
    assert evidence.status == "missing"


def test_limitation_not_success(tmp_path):
    proj = tmp_path / "no-wrapper"
    proj.mkdir()
    runner = SubprocessRunner()
    evidence = GradleTool(str(proj), runner=runner).build()
    assert evidence.status == "missing"
    assert "limitation" in evidence.message.lower()