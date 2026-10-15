"""CLI exam flow through the shared ``CommandRouter`` (007-examine).

The CLI and the TUI both route typed ``ExamineStartCommand`` /
``ExamineFinishCommand`` objects through the shared Router. These tests cover
that wiring end-to-end with a fake LLM client and a fake subprocess runner:
confirmation rules, ask counting from the event log (RQ-EXM-005/031), finish,
and a clean second exam without leaked ask counts.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "tests/actions/evaluate")
import ada_sensei.cli.router as router_mod  # noqa: E402
from ada_sensei.actions.examine import ExamineAction  # noqa: E402
from ada_sensei.cli.commands import (  # noqa: E402
    AskCommand,
    ErrorResponse,
    ExamFinishResult,
    ExamineFinishCommand,
    ExamineStartCommand,
    ExamStartResult,
)
from ada_sensei.cli.router import Router  # noqa: E402
from ada_sensei.config import Config  # noqa: E402
from helpers import FakeClient, Fixture  # noqa: E402


class OkRunner:
    """Fake subprocess runner that always succeeds."""

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


class RoutedExamine(ExamineAction):
    """Router-constructed examine action with the fake runner injected."""

    def __init__(self, services):
        super().__init__(services, runner=OkRunner())


def _statement(tmp_path) -> Path:
    statement = tmp_path / "exam.md"
    statement.write_text(
        "# Midterm Android Exam\n\n"
        "Allowed duration: 60 minutes\n"
        "Allowed /ask count: 4\n\n"
        "## Requirements\n\n"
        "- Implement a task repository backed by Room\n"
        "- Expose a ViewModel with UI state\n"
        "- Write unit tests for the repository\n",
        encoding="utf-8",
    )
    return statement


def _router(tmp_path, monkeypatch) -> Router:
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_test_report(proj, name="TaskRepoTest", tests=5, failures=0)
    Fixture.write_lint_report(
        proj, [{"severity": "info", "message": "ns", "file": "M.kt"}]
    )
    Fixture.write_detekt_report(
        proj, [{"severity": "info", "message": "ok", "line": "1"}]
    )
    config = Config(project={"path": str(proj)})
    config.data_dir = tmp_path / "data"
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    router.context.set_student("student://s1")
    router.context.set_project(str(proj))
    monkeypatch.setattr(router_mod, "ExamineAction", RoutedExamine)
    return router


def test_start_requires_confirmation(tmp_path, monkeypatch):
    router = _router(tmp_path, monkeypatch)
    result = router.dispatch(
        ExamineStartCommand(statement=str(_statement(tmp_path)))
    )
    assert isinstance(result, ErrorResponse)
    assert "confirmation" in result.message
    assert router.exam_status() is None


def test_finish_without_active_exam(tmp_path, monkeypatch):
    router = _router(tmp_path, monkeypatch)
    result = router.dispatch(ExamineFinishCommand(yes=True))
    assert isinstance(result, ErrorResponse)
    assert "active" in result.message
    assert router.exam_status() is None


def test_exam_flow_start_asks_finish(tmp_path, monkeypatch):
    router = _router(tmp_path, monkeypatch)
    statement = str(_statement(tmp_path))

    started = router.dispatch(ExamineStartCommand(statement=statement, yes=True))
    assert isinstance(started, ExamStartResult)
    assert router.exam_status() is not None
    assert router.exam_status().ask_count == 0
    assert router.exam_status().allowed_ask_count == 4

    router.dispatch(AskCommand(question="explain MVVM state"))
    assert router.exam_status().ask_count == 1

    router.dispatch(AskCommand(question="retry semantics?"))
    assert router.exam_status().ask_count == 2

    finished = router.dispatch(ExamineFinishCommand(yes=True))
    assert isinstance(finished, ExamFinishResult)
    report = Path(finished.report_path)
    assert report.exists()
    assert router.exam_status() is None


def test_second_exam_starts_clean(tmp_path, monkeypatch):
    router = _router(tmp_path, monkeypatch)
    statement = str(_statement(tmp_path))

    router.dispatch(ExamineStartCommand(statement=statement, yes=True))
    first_attempt = router.exam_status().exam_attempt_id
    router.dispatch(AskCommand(question="first exam ask"))
    assert router.exam_status().ask_count == 1
    router.dispatch(ExamineFinishCommand(yes=True))

    router.dispatch(ExamineStartCommand(statement=statement, yes=True))
    status = router.exam_status()
    assert status is not None
    assert status.ask_count == 0
    assert status.exam_attempt_id != first_attempt