"""RQ-EXM-018: the default exam rubric is unified-android:v2."""

from __future__ import annotations

import pytest
from ada_sensei.exams.models import ExamDefinitionError
from ada_sensei.exams.rubric import EXAM_RUBRIC, exam_engine, resolve_rubric


def test_exam_weights():
    weights = EXAM_RUBRIC.weights()
    assert EXAM_RUBRIC.ref == "unified-android:v2"
    assert weights["functional_requirements"] == pytest.approx(0.40)
    assert weights["tests"] == pytest.approx(0.20)
    assert weights["code_quality"] == pytest.approx(0.15)
    assert weights["mvvm"] == pytest.approx(0.15)
    assert weights["android_practices"] == pytest.approx(0.10)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_exam_engine_uses_unified_rubric():
    assert exam_engine().weights() == EXAM_RUBRIC.weights()


def test_unknown_or_legacy_rubric_reference_is_an_error():
    assert resolve_rubric(EXAM_RUBRIC.ref) is EXAM_RUBRIC
    with pytest.raises(ExamDefinitionError):
        resolve_rubric("evaluate-default:v1")
    with pytest.raises(ExamDefinitionError):
        resolve_rubric("exam-default:v1")