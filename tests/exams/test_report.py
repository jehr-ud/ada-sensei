"""RQ-EXM-024/029: the report is complete and discloses the generated grade."""

from __future__ import annotations

from ada_sensei.exams.models import (
    SUGGESTED_GRADE_LABEL,
    ExamResult,
    ExamStatus,
    ScoreCalculation,
)
from ada_sensei.exams.pdftext import extract_text
from ada_sensei.exams.report import ExamReportGenerator
from exams_helpers import make_attempt, make_definition, make_evidence


def _result() -> ExamResult:
    attempt = make_attempt(status=ExamStatus.completed)
    evidence = make_evidence()
    calculation = ScoreCalculation(
        rubric_id="exam-default",
        rubric_version="v1",
        raw_score_50=44,
        max_raw_score=50,
        suggested_grade=4.5,
        min_grade=1.0,
        max_grade=5.0,
        percentage=88.2,
        weighted_sum=0.75,
        weight_denominator=0.85,
    )
    return ExamResult(
        id="result://r1",
        student_id=attempt.student_id,
        project_id=attempt.project_id,
        exam_id=attempt.exam_id,
        exam_attempt_id=attempt.exam_attempt_id,
        attempt_id=attempt.attempt_id,
        exam_title=make_definition().title,
        rubric_id="exam-default",
        rubric_version="v1",
        overall_score=88.2,
        evidence=list(evidence.evidence),
        strengths=["clear separation of concerns"],
        weaknesses=["no error handling on IO"],
        feedback="Solid work.",
        limitations=["no student documentation matched"],
        score_calculation=calculation,
        raw_score_50=44,
        suggested_grade=4.5,
        ask_count=2,
        allowed_ask_count=4,
        duration_seconds=3600,
    )


def test_pdf_contains_required_sections(tmp_path):
    result = _result()
    generator = ExamReportGenerator(tmp_path / "output")
    path, report_id = generator.generate(result)
    payload = path.read_bytes()
    assert report_id
    assert payload.startswith(b"%PDF-")
    assert path.parent.name == "exams"

    text = generator.render_text(result)
    headings = generator._sections(result)
    for heading, _ in headings:
        assert f"## {heading}" in text

    extracted = extract_text(payload)
    # The cover and calculation table carry the identification, rubric and
    # calculation sections (RQ-EXM-024).
    for label in (
        "ADA Sensei",
        "Exam assessment report",
        "Student",
        "Project",
        "Exam attempt",
        "Report id",
        "Rubric",
        "Score calculation",
    ):
        assert label in extracted
    # The PDF's detail sections mirror the report text sections.
    for heading, _ in headings:
        assert heading in extracted


def test_suggested_grade_disclosure(tmp_path):
    result = _result()
    text = ExamReportGenerator(tmp_path / "output").render_text(result)
    assert result.grade_disclosure == SUGGESTED_GRADE_LABEL
    assert SUGGESTED_GRADE_LABEL in text