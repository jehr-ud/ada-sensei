from __future__ import annotations

import json

import pytest
from ada_sensei.actions.examine import ExamFinishResult
from ada_sensei.evaluation import (
    DEFAULT_MODEL,
    PROMPT_VERSION,
    CriterionStatus,
    EvaluatorAgent,
    EvidenceContext,
    LLMCriterionDecision,
    LLMRequirementEvaluator,
    LLMRunMetadata,
    OverallStatus,
)
from ada_sensei.evaluation.exam_agent import LLM_STATUS_TO_SCORE_5
from ada_sensei.evaluation.llm_evaluators import (
    PROMPT_ID,
    LLMArchitectureEvaluator,
)
from ada_sensei.exams.models import (
    ExamDefinition,
    ExamRequirement,
    ExamResult,
    ScoreCalculation,
)
from ada_sensei.exams.pdf import PdfError
from ada_sensei.exams.pdftext import extract_text
from ada_sensei.exams.report import ExamReportGenerator
from ada_sensei.exams.scoring import ExamScorer
from ada_sensei.llm.base import LLMClient
from ada_sensei.models import Evidence


class ScriptedClient(LLMClient):
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, messages, *, model=None, temperature=None) -> str:
        raise AssertionError("v2 evaluators must use chat_structured")

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ) -> str:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "json_schema": json_schema,
                "temperature": temperature,
            }
        )
        if not self.responses:
            return "{}"
        return self.responses.pop(0)


def _context(tmp_path, *, line_end: int = 1) -> EvidenceContext:
    source = tmp_path / "Task.kt"
    source.write_text("class Task {}\n", encoding="utf-8")
    evidence = Evidence(
        id="ev://task",
        source="structure",
        type="structure",
        status="pass",
        file="Task.kt",
        line=1,
        line_start=1,
        line_end=line_end,
        symbol="Task",
        excerpt="class Task {}",
        content_hash="sha256:abc",
        collector="fixture",
        reliability="observed",
    )
    return EvidenceContext(
        project_id="project://p1",
        project_path=str(tmp_path),
        evidence=[evidence],
    )


def _criterion(criterion_id="AC1"):
    from ada_sensei.evaluation.llm_evaluators import EvaluationCriterionInput

    return EvaluationCriterionInput(
        criterion_id=criterion_id,
        description="The repository exposes CRUD operations",
    )


def _definition() -> ExamDefinition:
    return ExamDefinition(
        exam_id="exam://e1",
        title="v2 fixture exam",
        requirements=[
            ExamRequirement(
                requirement_id="req://fr1",
                description="repository with CRUD operations",
                weight=1.0,
            )
        ],
        allowed_duration_seconds=3600,
        allowed_ask_count=4,
    )


def test_requirement_evaluator_accepts_grounded_decision(tmp_path):
    client = ScriptedClient(
        json.dumps(
            {
                "criteria": [
                    {
                        "criterion_id": "AC1",
                        "status": "PASS",
                        "reason": "CRUD methods are visible in the repository",
                        "evidence_ids": ["ev://task"],
                        "limitations": [],
                        "recommended_action": "none",
                        "confidence": 0.9,
                    }
                ]
            }
        )
    )
    batch = LLMRequirementEvaluator(client).evaluate(
        [_criterion()], _context(tmp_path)
    )

    assert [item.status for item in batch.decisions] == ["PASS"]
    assert batch.decisions[0].evidence_ids == ["ev://task"]
    assert batch.run.validation_status == "VALIDATED"
    assert batch.run.model_id == DEFAULT_MODEL
    assert batch.run.prompt_id == PROMPT_ID
    assert batch.run.prompt_version == PROMPT_VERSION
    assert batch.run.temperature == 0.0
    assert batch.run.attempts == 1
    assert client.calls[0]["temperature"] == 0.0


def test_single_decision_object_is_wrapped_before_validation(tmp_path):
    client = ScriptedClient(
        json.dumps(
            {
                "criterion_id": "AC1",
                "status": "PASS",
                "reason": "CRUD methods are visible in the repository",
                "evidence_ids": ["ev://task"],
                "limitations": [],
                "recommended_action": "none",
                "confidence": 0.9,
            }
        )
    )

    batch = LLMRequirementEvaluator(client).evaluate(
        [_criterion()], _context(tmp_path)
    )

    assert len(client.calls) == 1
    assert [item.status for item in batch.decisions] == ["PASS"]
    assert batch.run.validation_status == "VALIDATED"


def test_invalid_evidence_reference_is_downgraded(tmp_path):
    client = ScriptedClient(
        json.dumps(
            {
                "criteria": [
                    {
                        "criterion_id": "AC1",
                        "status": "PASS",
                        "reason": "claimed without a real line",
                        "evidence_ids": ["ev://task"],
                        "limitations": [],
                        "recommended_action": "none",
                        "confidence": 0.8,
                    }
                ]
            }
        )
    )
    batch = LLMRequirementEvaluator(client).evaluate(
        [_criterion()], _context(tmp_path, line_end=99)
    )

    decision = batch.decisions[0]
    assert decision.status == "NOT_EVALUATED"
    assert decision.reason_code == "INVALID_EVIDENCE_REFERENCE"
    assert decision.evidence_ids == []
    assert batch.run.validation_status == "PARTIAL"
    assert batch.run.limitations


def test_invalid_json_retries_three_times_without_scoring(tmp_path):
    client = ScriptedClient("not json", "still not json", "bad again")
    batch = LLMRequirementEvaluator(client).evaluate(
        [_criterion()], _context(tmp_path)
    )

    assert len(client.calls) == 3
    assert batch.run.attempts == 3
    assert batch.run.validation_status == "FAILED"
    assert all(item.status == "NOT_EVALUATED" for item in batch.decisions)
    assert all(item.reason_code == "LLM_INVALID_OUTPUT" for item in batch.decisions)


def test_invalid_decision_is_retried_and_never_scored(tmp_path):
    client = ScriptedClient(
        json.dumps(
            {
                "criteria": [
                    {
                        "criterion_id": "AC1",
                        "status": "PASS",
                        "explanation": "alias for reason",
                        "evidence_ids": ["ev://task"],
                        "limitations": [],
                        "recommended_action": "none",
                        "confidence": 0.9,
                    }
                ]
            }
        )
    )

    batch = LLMRequirementEvaluator(client).evaluate(
        [_criterion()], _context(tmp_path)
    )

    assert len(client.calls) == 3
    assert batch.run.attempts == 3
    assert batch.run.validation_status == "FAILED"
    assert all(item.status == "NOT_EVALUATED" for item in batch.decisions)
    assert LLM_STATUS_TO_SCORE_5.get(batch.decisions[0].status) is None


def test_empty_decision_payload_is_retried_and_never_scored(tmp_path):
    client = ScriptedClient("{}")

    batch = LLMRequirementEvaluator(client).evaluate(
        [_criterion()], _context(tmp_path)
    )

    assert len(client.calls) == 3
    assert batch.run.attempts == 3
    assert batch.run.validation_status == "FAILED"
    assert all(item.status == "NOT_EVALUATED" for item in batch.decisions)


def test_missing_client_never_produces_zero(tmp_path):
    batch = LLMRequirementEvaluator(None).evaluate(
        [_criterion()], _context(tmp_path)
    )

    assert batch.run.validation_status == "FAILED"
    assert batch.run.limitations == ["LLM_UNAVAILABLE"]
    assert batch.decisions[0].status == "NOT_EVALUATED"
    assert batch.decisions[0].reason_code == "LLM_UNAVAILABLE"
    assert LLM_STATUS_TO_SCORE_5.get(batch.decisions[0].status) is None


def test_architecture_evaluator_covers_both_matrices():
    criteria = LLMArchitectureEvaluator(None).criteria()
    clean = [item for item in criteria if item.subdimension == "clean_architecture"]
    mvvm = [item for item in criteria if item.subdimension == "mvvm"]

    assert [item.criterion_id for item in clean] == [f"C{n}" for n in range(1, 8)]
    assert [item.criterion_id for item in mvvm] == [f"M{n}" for n in range(1, 7)]
    assert all(item.dimension == "mvvm" for item in criteria)


def test_architecture_score_uses_declared_subweights_and_coverage():
    decisions = {
        f"C{n}": LLMCriterionDecision(
            criterion_id=f"C{n}",
            status="PASS",
            reason="observed",
            evidence_ids=["ev://task"],
            limitations=[],
            recommended_action="none",
            confidence=1.0,
        )
        for n in range(1, 8)
    }
    decisions["M1"] = LLMCriterionDecision(
        criterion_id="M1",
        status="PARTIAL",
        reason="partial state flow",
        evidence_ids=["ev://task"],
        limitations=[],
        recommended_action="none",
        confidence=0.5,
    )
    score, coverage = ExamScorer().architecture_score_from_decisions(decisions)

    assert score == pytest.approx(0.5 * 4 + (0.5 / 6) * 2)
    assert coverage == pytest.approx(0.5 + 0.5 / 6)


def test_llm_unavailable_marks_the_single_report_blocked(tmp_path):
    run = EvaluatorAgent().build_report(
        result=ExamResult(
            student_id="student://s1",
            project_id="project://p1",
            exam_id="exam://e1",
            exam_attempt_id="exam_attempt://a1",
            attempt_id="attempt://a1",
            rubric_id="unified-android",
            rubric_version="v2",
        ),
        definition=_definition(),
        evidence=_context(tmp_path),
        requirement_decisions={
            "AC1": LLMCriterionDecision(
                criterion_id="AC1",
                status="NOT_EVALUATED",
                reason="no LLM client is configured",
                evidence_ids=[],
                limitations=["LLM_UNAVAILABLE"],
                recommended_action="provide the missing model",
                confidence=0.0,
                reason_code="LLM_UNAVAILABLE",
            )
        },
        llm_runs=[
            LLMRunMetadata(
                provider="ollama",
                model_id=DEFAULT_MODEL,
                prompt_id=PROMPT_ID,
                prompt_version=PROMPT_VERSION,
                temperature=0.0,
                attempts=0,
                validation_status="FAILED",
                limitations=["LLM_UNAVAILABLE"],
            )
        ],
    )

    assert run.overall_status is OverallStatus.BLOCKED
    assert run.overall_score_50 is None
    assert run.criterion_results[0].status is CriterionStatus.NOT_EVALUATED
    assert run.criterion_results[0].score is None


def test_pdf_stays_compact_and_auditable_with_many_findings(tmp_path):
    findings = [
        Evidence(
            id=f"ev://finding-{index}",
            source="detekt",
            type="error",
            status="fail",
            message="LongParameterList reported by detekt",
            file=f"app/src/main/java/F{index}.kt",
        )
        for index in range(60)
    ]
    context = EvidenceContext(project_id="project://p1", evidence=findings)
    calculation = ScoreCalculation(
        rubric_id="unified-android",
        rubric_version="v2",
        raw_score_50=None,
        max_raw_score=50,
    )
    result = ExamResult(
        student_id="student://s1",
        project_id="project://p1",
        exam_id="exam://e1",
        exam_attempt_id="exam_attempt://a1",
        attempt_id="attempt://a1",
        exam_title="Compact report",
        rubric_id="unified-android",
        rubric_version="v2",
        score_calculation=calculation,
    )
    result.evaluation_report = EvaluatorAgent().build_report(
        result=result, definition=_definition(), evidence=context
    )
    generator = ExamReportGenerator(tmp_path)

    try:
        path, _ = generator.generate(result)
    except PdfError:
        pytest.fail("report exceeded the four-page limit")
    extracted = extract_text(path.read_bytes())
    groups = [
        line
        for line in extracted.splitlines()
        if line.startswith("Finding group:")
    ]

    assert len(groups) <= 8
    assert "Attempt exam_attempt://a1" in extracted
    assert "6. Tests and code quality" in extracted
    assert "{{" not in extracted


def test_reevaluation_link_is_preserved(tmp_path):
    result = ExamResult(
        student_id="student://s1",
        project_id="project://p1",
        exam_id="exam://e1",
        exam_attempt_id="exam_attempt://a1",
        attempt_id="attempt://a1",
        rubric_id="unified-android",
        rubric_version="v2",
        supersedes_report_id="evaluation_report://previous",
    )
    report = EvaluatorAgent().build_report(
        result=result, definition=_definition(), evidence=_context(tmp_path)
    )

    assert report.supersedes_report_id == "evaluation_report://previous"


def test_finish_presentation_reads_the_official_report(tmp_path):
    calculation = ScoreCalculation(
        rubric_id="unified-android",
        rubric_version="v2",
        raw_score_50=44,
        max_raw_score=50,
        suggested_grade=4.5,
        max_grade=5.0,
    )
    result = ExamResult(
        student_id="student://s1",
        project_id="project://p1",
        exam_id="exam://e1",
        exam_attempt_id="exam_attempt://a1",
        attempt_id="attempt://a1",
        exam_title="Official report",
        rubric_id="unified-android",
        rubric_version="v2",
        score_calculation=calculation,
        raw_score_50=44,
        suggested_grade=4.5,
        locale="en-US",
    )
    result.evaluation_report = EvaluatorAgent().build_report(
        result=result,
        definition=_definition(),
        evidence=_context(tmp_path),
    )
    presented = ExamFinishResult(result=result, report_path="/tmp/report.pdf").present()

    report = result.evaluation_report
    assert f"Raw score: {report.overall_score_50}/50" in presented
    assert f"Suggested grade: {report.suggested_grade}/5.0" in presented
    assert f"Evaluation status: {report.overall_status.value}" in presented
    assert "Coverage:" in presented
