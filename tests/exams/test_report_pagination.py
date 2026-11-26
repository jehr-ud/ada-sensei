"""RQ-EXM-099: adaptive pagination keeps the full auditable report."""

from __future__ import annotations

import pytest
from ada_sensei.evaluation import EvaluatorAgent
from ada_sensei.evaluation.models import CriterionResult, CriterionStatus, Limitation
from ada_sensei.exams.models import ExamResult, ExamStatus, ScoreCalculation
from ada_sensei.exams.pdftext import extract_page_texts
from ada_sensei.exams.report import ExamReportGenerator
from exams_helpers import make_attempt, make_definition, make_evidence


def _result(extra_limitations: int) -> ExamResult:
    attempt = make_attempt(status=ExamStatus.completed)
    evidence = make_evidence()
    calculation = ScoreCalculation(
        rubric_id="unified-android",
        rubric_version="v1",
        raw_score_50=44,
        max_raw_score=50,
        suggested_grade=4.5,
        min_grade=1.0,
        max_grade=5.0,
    )
    result = ExamResult(
        id="result://r1",
        student_id=attempt.student_id,
        project_id=attempt.project_id,
        exam_id=attempt.exam_id,
        exam_attempt_id=attempt.exam_attempt_id,
        attempt_id=attempt.attempt_id,
        exam_title="Test exam",
        rubric_id="unified-android",
        rubric_version="v1",
        overall_score=88.2,
        evidence=list(evidence.evidence),
        score_calculation=calculation,
        raw_score_50=44,
        suggested_grade=4.5,
    )
    result.evaluation_report = EvaluatorAgent().build_report(
        result=result,
        definition=make_definition(),
        evidence=evidence,
    )
    report = result.evaluation_report
    assert report is not None
    report.criterion_results.append(
        CriterionResult(
            criterion_id="REQ-EVIDENCE",
            dimension="functional_requirements",
            status=CriterionStatus.PASS,
            score=1.0,
            weight=1.0,
            weighted_score=1.0,
            evidence_ids=[ref.evidence_id for ref in report.evidence[:2]],
            analyzer="test",
            analyzer_version="1.0",
            rule_version="1.0",
            requirement_id="req://fr1",
        )
    )
    for index in range(extra_limitations):
        report.limitations.append(
            Limitation(
                limitation_id=f"lim://extra-{index}",
                dimension="functional_requirements",
                reason_code="CALIBRATION",
                description=(
                    f"CALIBRATION-EXTRA-{index} " + "long calibration limitation " * 8
                ),
                coverage_impact="none",
                required_action="none",
            )
        )
    return result


@pytest.mark.parametrize(
    ("extra_limitations", "expected_pages"),
    [(50, 4), (70, 5), (90, 6)],
)
def test_report_uses_as_many_pages_as_content_needs(
    tmp_path, extra_limitations: int, expected_pages: int
):
    result = _result(extra_limitations)
    generator = ExamReportGenerator(tmp_path)
    path, report_id = generator.generate(result)

    pages = extract_page_texts(path.read_bytes())
    assert report_id
    assert len(pages) == expected_pages
    assert all(page.strip() for page in pages)
    for index, page in enumerate(pages, start=1):
        assert f"Page {index} of {expected_pages}" in page
        assert any(
            line
            for line in page.splitlines()
            if not line.startswith(("Attempt ", "Page ", "Report "))
        )

    text = "\n".join(pages)
    for heading, _ in generator._sections(result):
        assert heading in text
    assert f"CALIBRATION-EXTRA-{extra_limitations - 1}" in text
    assert "app/src/main/java/com/example/app/TaskRepository.kt" in text
