"""RQ-EXM-064/068/069/073/074: toolchain preflight is part of exam start."""

from __future__ import annotations

import pytest
from ada_sensei.actions.examine import ExamineAction, ExamStartInput
from ada_sensei.evaluation import EvaluatorAgent, OverallStatus
from ada_sensei.exams.models import ExamResult, ExamStateError, ExamStatus
from ada_sensei.exams.scoring import ExamScorer
from ada_sensei.exams.store import ExamStore
from exams_helpers import (
    STATEMENT_JSON,
    OkRunner,
    make_attempt,
    make_context,
    make_definition,
    make_evidence,
    make_project,
)
from tests.toolchain.helpers import BlockedToolchainManager, ReadyToolchainManager


def _statement(tmp_path):
    path = tmp_path / "exam.json"
    path.write_text(STATEMENT_JSON, encoding="utf-8")
    return path


def test_blocked_toolchain_creates_no_attempt(tmp_path):
    project = make_project(tmp_path)
    services = make_context(tmp_path, project)
    store = ExamStore(services.data_dir)
    action = ExamineAction(
        services, runner=OkRunner(), toolchain=BlockedToolchainManager()
    )

    with pytest.raises(ExamStateError, match="toolchain"):
        action.start(
            ExamStartInput(
                statement=str(_statement(tmp_path)),
                project_id="project://p1",
                confirmed=True,
            )
        )

    assert store.list_ids() == []
    assert services.context.exam_attempt_id is None


def test_ready_toolchain_is_persisted_on_attempt(tmp_path):
    project = make_project(tmp_path)
    services = make_context(tmp_path, project)
    toolchain = ReadyToolchainManager()
    action = ExamineAction(
        services, runner=OkRunner(), toolchain=toolchain
    )

    started = action.start(
        ExamStartInput(
            statement=str(_statement(tmp_path)),
            project_id="project://p1",
            confirmed=True,
        )
    )
    stored = ExamStore(services.data_dir).get(started.attempt.exam_attempt_id)

    assert stored is not None
    assert stored.toolchain_manifest == toolchain.manifest
    assert [item.tool_id for item in stored.toolchain_evidence] == [
        "android_lint",
        "detekt",
        "ktlint",
    ]


def test_infrastructure_failure_has_no_final_score(tmp_path):
    definition = make_definition()
    evidence = make_evidence()
    toolchain = BlockedToolchainManager()
    preparation = toolchain.prepare(make_project(tmp_path))
    attempt = make_attempt(status=ExamStatus.completed)
    calculation = ExamScorer().score(definition, evidence, attempt=attempt)
    result = ExamResult(
        student_id=attempt.student_id,
        project_id=attempt.project_id,
        exam_id=attempt.exam_id,
        exam_attempt_id=attempt.exam_attempt_id,
        attempt_id=attempt.attempt_id,
        exam_title=definition.title,
        rubric_id=calculation.rubric_id,
        rubric_version=calculation.rubric_version,
        evidence=list(evidence.evidence),
        criteria=ExamScorer().functional_criteria(definition, evidence),
        score_calculation=calculation,
        raw_score_50=calculation.raw_score_50,
        suggested_grade=calculation.suggested_grade,
        locale="en-US",
    )

    report = EvaluatorAgent().build_report(
        result=result,
        definition=definition,
        evidence=evidence,
        toolchain_preparation=preparation,
    )

    assert report.overall_status is OverallStatus.INCOMPLETE_INFRASTRUCTURE
    assert report.overall_score_5 is None
    assert report.overall_score_50 is None
    assert report.suggested_grade is None
    assert report.toolchain_manifest == toolchain.manifest
    assert report.toolchain_evidence == preparation.executions
    assert any(
        item.reason_code == "toolchain_preparation_failed"
        for item in report.limitations
    )
