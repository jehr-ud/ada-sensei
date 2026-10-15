"""RQ-EXM-001: the five identities stay separate and are never inferred."""

from __future__ import annotations

from ada_sensei.exams.models import ExamAttempt, ExamResult

EXAM_ATTEMPT = "exam_attempt://ea1"
STUDENT = "student://maria"
PROJECT = "project://p77"
EXAM = "exam://x99"
ATTEMPT = "attempt://a42"


def test_identities_are_separate():
    attempt = ExamAttempt(
        exam_attempt_id=EXAM_ATTEMPT,
        student_id=STUDENT,
        project_id=PROJECT,
        exam_id=EXAM,
        attempt_id=ATTEMPT,
    )
    distinct = {
        attempt.exam_attempt_id,
        attempt.student_id,
        attempt.project_id,
        attempt.exam_id,
        attempt.attempt_id,
    }
    assert len(distinct) == 5
    assert attempt.exam_attempt_id == EXAM_ATTEMPT
    assert attempt.student_id == STUDENT
    assert attempt.project_id == PROJECT
    assert attempt.exam_id == EXAM
    assert attempt.attempt_id == ATTEMPT


def test_exam_result_keeps_identities_apart():
    result = ExamResult(
        id="result://r1",
        student_id=STUDENT,
        project_id=PROJECT,
        exam_id=EXAM,
        exam_attempt_id=EXAM_ATTEMPT,
        attempt_id=ATTEMPT,
    )
    assert result.student_id == STUDENT
    assert result.project_id == PROJECT
    assert result.exam_id == EXAM
    assert result.exam_attempt_id == EXAM_ATTEMPT
    assert result.attempt_id == ATTEMPT
    with_no_exam = result.model_copy(update={"exam_id": None, "attempt_id": None})
    assert with_no_exam.exam_attempt_id == EXAM_ATTEMPT