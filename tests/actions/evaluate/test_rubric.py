from __future__ import annotations

import pytest
from ada_sensei.actions.evaluate import Rubric
from ada_sensei.models import EvaluationCriterion, Evidence


class Fixtures:
    @staticmethod
    def make_requirements():
        return [
            EvaluationCriterion(
                requirement_id="req://r1",
                dimension="functional_requirements",
                weight=0.5,
                score=4,
            ),
            EvaluationCriterion(
                requirement_id="req://r2",
                dimension="functional_requirements",
                weight=0.5,
                score=0,
            ),
        ]


def test_rubric_weights():
    assert Rubric.weights["functional_requirements"] == 0.40
    assert Rubric.weights["tests"] == 0.20
    assert Rubric.weights["code_quality"] == 0.15
    assert Rubric.weights["architecture"] == 0.15
    assert Rubric.weights["android_practices"] == 0.10
    assert abs(sum(Rubric.weights.values()) - 1.0) < 1e-9


def test_subweights_inside_functional_dimension():
    Rubric.validate_weights(Fixtures.make_requirements())
    with pytest.raises(ValueError):
        Rubric.validate_weights(
            [
                EvaluationCriterion(
                    requirement_id="req://r1",
                    dimension="functional_requirements",
                    weight=0.2,
                )
            ]
        )


def test_deterministic_scores():
    tests = [
        Evidence(source="test", type="unit_test", status="pass"),
        Evidence(source="test", type="unit_test", status="pass"),
    ]
    assert Rubric.dimension_score("tests", tests) == 4

    lint_ok = [
        Evidence(
            source="lint",
            type="android_lint",
            status="pass",
            severity="warning",
            message="namespace missing",
        )
    ]
    assert Rubric.dimension_score("android_practices", lint_ok) == 3


def test_not_evaluated_excluded():
    dims = {
        "tests": None,
        "code_quality": 4,
        "architecture": None,
        "android_practices": None,
    }
    score, final = Rubric.compute(dims)
    assert score is not None
    assert score == 100.0 * (0.15 * 4 / 4) / 0.15


def test_no_dimension_evaluated_no_score():
    dims = {
        "tests": None,
        "code_quality": None,
        "architecture": None,
        "android_practices": None,
    }
    score, final = Rubric.compute(dims)
    assert score is None
    assert final["tests"] is None


def test_weighted_score():
    score, _ = Rubric.compute(
        {
            "tests": 4,
            "code_quality": 3,
            "architecture": 4,
            "android_practices": 2,
        },
        Fixtures.make_requirements(),
    )
    assert score is not None
    # functional = (0.5*4 + 0.5*0) = 2.0
    expected = (
        100
        * (0.40 * 2.0 / 4 + 0.20 * 4 / 4 + 0.15 * 3 / 4 + 0.15 * 4 / 4 + 0.10 * 2 / 4)
        / (0.40 + 0.20 + 0.15 + 0.15 + 0.10)
    )
    assert score == pytest.approx(expected, abs=0.06)


def test_requirement_score_passing_unit_test():
    c = EvaluationCriterion(
        requirement_id="req://r1",
        evidence=[
            Evidence(source="test", type="unit_test", status="pass"),
            Evidence(source="build", type="compilation", status="pass"),
        ],
    )
    assert Rubric.requirement_score(c) == 4


def test_requirement_score_failing():
    c = EvaluationCriterion(
        requirement_id="req://r1",
        evidence=[
            Evidence(source="test", type="unit_test", status="fail"),
        ],
    )
    assert Rubric.requirement_score(c) == 0


def test_requirement_score_no_evidence():
    c = EvaluationCriterion(requirement_id="req://r1", evidence=[])
    assert Rubric.requirement_score(c) is None


def test_structured_result():
    criteria = Fixtures.make_requirements()
    score, final = Rubric.compute(
        {"tests": 4, "code_quality": 4, "architecture": 4, "android_practices": 4},
        criteria,
    )
    assert isinstance(score, float)
    assert final["functional_requirements"] == pytest.approx(2.0)


def test_compile_failure_marks_not_evaluated():
    dims = {
        "tests": None,
        "code_quality": None,
        "architecture": None,
        "android_practices": None,
    }
    score, _ = Rubric.compute(dims, [])
    assert score is None