"""RQ-EXM-100/101: PDF persistence, failures, and report-only retry."""

from __future__ import annotations

from pathlib import Path

import pytest
from ada_sensei.actions.examine import (
    ExamFinishInput,
    ExamineAction,
    ExamPdfRetryError,
    ExamStartInput,
)
from ada_sensei.exams.models import ExamResult
from exams_helpers import STATEMENT_JSON, OkRunner, make_context, make_project
from tests.toolchain.helpers import ReadyToolchainManager


def _action_with_exam(tmp_path):
    project = make_project(tmp_path)
    statement = tmp_path / "exam.json"
    statement.write_text(STATEMENT_JSON, encoding="utf-8")
    services = make_context(tmp_path, project, student="student://s1")
    action = ExamineAction(
        services, runner=OkRunner(), toolchain=ReadyToolchainManager()
    )
    action.start(
        ExamStartInput(
            statement=str(statement), project_id="project://p1", confirmed=True
        )
    )
    return action, services


def test_finish_persists_report_before_pdf_generation(tmp_path, monkeypatch):
    action, services = _action_with_exam(tmp_path)
    calls: list[str] = []
    original_save = services.results.save
    original_generate = action.reports.generate

    def tracked_save(result):
        calls.append("save")
        assert result.evaluation_report is not None
        return original_save(result)

    def tracked_generate(*args, **kwargs):
        calls.append("pdf")
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(services.results, "save", tracked_save)
    monkeypatch.setattr(action.reports, "generate", tracked_generate)

    finished = action.finish(ExamFinishInput(confirmed=True))

    assert calls.index("save") < calls.index("pdf")
    assert finished.result.pdf_status == "generated"
    persisted = services.results.get(finished.result.id)
    assert persisted is not None
    assert persisted.evaluation_report is not None
    assert persisted.pdf_status == "generated"
    assert Path(finished.report_path).exists()


def test_pdf_failure_keeps_report_and_finishes_evaluation(tmp_path, monkeypatch):
    action, services = _action_with_exam(tmp_path)

    def fail_generate(*_args, **_kwargs):
        raise RuntimeError("pdf device unavailable")

    monkeypatch.setattr(action.reports, "generate", fail_generate)

    finished = action.finish(ExamFinishInput(confirmed=True))

    assert finished.result.pdf_status == "failed"
    assert "RuntimeError: pdf device unavailable" in finished.result.pdf_error
    assert not Path(finished.report_path).exists()

    persisted = services.results.get(finished.result.id)
    assert persisted is not None
    assert persisted.evaluation_report is not None
    assert persisted.pdf_status == "failed"
    assert persisted.pdf_error

    attempt = action.store.get(finished.result.exam_attempt_id)
    assert attempt is not None
    assert attempt.status == "completed"


def test_retry_reuses_report_without_second_evaluation(tmp_path, monkeypatch):
    action, services = _action_with_exam(tmp_path)
    finished = action.finish(ExamFinishInput(confirmed=True))
    evaluation_id = finished.result.report_id
    result_ids = set(services.results.list_ids())
    assert evaluation_id

    def forbidden(*_args, **_kwargs):
        raise AssertionError("retry must not evaluate again")

    monkeypatch.setattr(action, "_assemble", forbidden)
    monkeypatch.setattr(action.engine, "collect_evidence", forbidden)
    monkeypatch.setattr(action._runner, "run", forbidden)
    monkeypatch.setattr(services.attempts, "save", forbidden)

    retried = action.retry_report_pdf(finished.result.id)

    assert retried.result.report_id == evaluation_id
    report = retried.result.evaluation_report
    assert report is not None
    assert report.report_id == evaluation_id
    assert retried.result.pdf_status == "generated"
    assert Path(retried.report_path).exists()
    assert set(services.results.list_ids()) == result_ids


def test_retry_rejects_missing_persisted_report(tmp_path):
    action, services = _action_with_exam(tmp_path)
    result = ExamResult(
        id="result://no-report",
        student_id="student://s1",
        project_id="project://p1",
        exam_id="exam://e1",
        exam_attempt_id="exam_attempt://a1",
        attempt_id="attempt://a1",
    )
    services.results.save(result)

    with pytest.raises(ExamPdfRetryError, match="no persisted EvaluationReport"):
        action.retry_report_pdf(result.id)
