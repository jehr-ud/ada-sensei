"""The official typed evaluation report is deterministic and traceable."""

from __future__ import annotations

import re

import pytest
from ada_sensei.evaluation import EvaluatorAgent, OverallStatus
from ada_sensei.exams.models import ExamResult, ExamStatus
from ada_sensei.exams.pdftext import extract_text
from ada_sensei.exams.report import ExamReportGenerator
from ada_sensei.exams.scoring import ExamScorer
from exams_helpers import make_attempt, make_definition, make_evidence
from pydantic import ValidationError


def _result():
    definition = make_definition()
    evidence = make_evidence()
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
        locale="es-CO",
    )
    report = EvaluatorAgent().build_report(
        result=result,
        definition=definition,
        evidence=evidence,
    )
    result.evaluation_report = report
    return result, definition


def test_report_contains_all_dimensions_and_scores():
    result, _ = _result()
    report = result.evaluation_report

    assert report is not None
    assert report.overall_status is OverallStatus.COMPLETE
    assert [item.dimension_id for item in report.dimension_results] == [
        item.dimension for item in result.score_calculation.lines
    ]
    assert report.overall_score_5 is not None
    assert report.overall_score_50 == round(report.overall_score_5 * 10)
    assert report.ruleset_versions


def test_report_rejects_non_evaluable_criterion_with_score():
    from ada_sensei.evaluation.models import CriterionResult, CriterionStatus

    with pytest.raises(ValidationError):
        CriterionResult(
            criterion_id="T1",
            dimension="tests",
            status=CriterionStatus.NOT_EVALUATED,
            score=4.0,
            weight=0.5,
            weighted_score=2.0,
            analyzer="unit_test_reports",
            analyzer_version="v1",
            rule_version="v1",
        )


def test_report_generator_renders_r1_to_r12(tmp_path):
    result, definition = _result()
    generator = ExamReportGenerator(tmp_path)
    text = generator.render_text(result)
    headings = [heading for heading, _ in generator._sections(result)]

    assert [h for h in headings if re.match(r"R\d+ ", h)] == [
        "R1 Identification",
        "R2 Global summary",
        "R3 Dimension result",
        "R4 Functional requirements",
        "R5 Unit tests",
        "R6 Code quality",
        "R7 MVVM",
        "R8 Android practices",
        "R9 Tool status",
        "R10 Exam metrics",
        "R11 Deterministic observations",
        "R12 Limitations and traceability",
    ]
    assert "Status: COMPLETE" in text
    path, _ = generator.generate(result, definition)
    extracted = extract_text(path.read_bytes())
    assert "R1 Identification" in extracted
    assert "R12 Limitations and traceability" in extracted
