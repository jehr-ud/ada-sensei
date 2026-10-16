"""Exam locale snapshot: start records it, finish reports with it (RQ-LNG-013)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "tests/actions/evaluate")

import ada_sensei.cli.router as router_mod  # noqa: E402
from ada_sensei.actions.examine import ExamineAction  # noqa: E402
from ada_sensei.cli.commands import (  # noqa: E402
    ExamFinishResult,
    ExamineFinishCommand,
    ExamineStartCommand,
    LanguageCommand,
)
from ada_sensei.cli.router import Router  # noqa: E402
from ada_sensei.config import Config  # noqa: E402
from ada_sensei.exams.report import ExamReportGenerator  # noqa: E402
from helpers import FakeClient, Fixture  # noqa: E402


class OkRunner:
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


def test_start_snapshots_active_locale(tmp_path, monkeypatch):
    router = _router(tmp_path, monkeypatch)
    router.dispatch(LanguageCommand(locale="es-CO"))
    started = router.dispatch(
        ExamineStartCommand(statement=str(_statement(tmp_path)), yes=True)
    )
    assert started.attempt.locale == "es-CO"


def test_finish_uses_snapshot_despite_later_switch(tmp_path, monkeypatch):
    router = _router(tmp_path, monkeypatch)
    router.dispatch(LanguageCommand(locale="es-CO"))
    router.dispatch(ExamineStartCommand(statement=str(_statement(tmp_path)), yes=True))
    router.dispatch(LanguageCommand(locale="en-US"))
    finished = router.dispatch(ExamineFinishCommand(yes=True))
    assert isinstance(finished, ExamFinishResult)
    assert finished.result.locale == "es-CO"
    text = ExamReportGenerator(tmp_path / "reports").render_text(finished.result)
    assert "Language: Español (es-CO)" in text


def test_legacy_attempt_without_snapshot_renders_as_before(tmp_path):
    from ada_sensei.exams.models import ExamResult

    result = ExamResult(student_id="s", project_id="p")
    assert result.locale is None
    text = ExamReportGenerator(tmp_path / "reports").render_text(result)
    assert "Language:" not in text
