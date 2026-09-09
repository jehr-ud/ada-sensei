from __future__ import annotations

from ada_sensei.models import (
    Answer,
    Attempt,
    AttemptStatus,
    EvaluationCriterion,
    EvaluationResult,
    Exercise,
    Requirement,
)
from ada_sensei.urns import URN


class Assertions:
    @staticmethod
    def ids_are_distinct(*ids):
        return len({id.split("://")[0] for id in ids}) == len(ids)


def test_required_fields():
    exercise = Exercise(title="t", statement="s")
    assert exercise.id.startswith("exercise://")
    attempt = Attempt()
    assert attempt.status == AttemptStatus.in_progress
    answer = Answer()
    assert answer.id.startswith("answer://")
    result = EvaluationResult()
    assert result.id.startswith("result://")


def test_stable_ids():
    req = Requirement(summary="add tasks")
    assert req.id.startswith("req://")
    exercise = Exercise(requirements=[req])
    dumped = exercise.model_dump(mode="json")
    loaded = Exercise.model_validate(dumped)
    assert loaded.id == exercise.id
    assert loaded.requirements[0].id == req.id

    criterion = EvaluationCriterion(requirement_id=req.id)
    assert criterion.requirement_id == req.id


def test_id_distinctness():
    exercise = Exercise()
    attempt = Attempt()
    result = EvaluationResult()
    kinds = {
        attempt.id.split("://")[0],
        exercise.id.split("://")[0],
        result.id.split("://")[0],
    }
    assert kinds == {"attempt", "exercise", "result"}
    assert Assertions.ids_are_distinct(exercise.id, attempt.id, result.id)

    p1 = URN.project_id_from_path("/a/b/proj")
    p2 = URN.project_id_from_path("/a/b/proj")
    p3 = URN.project_id_from_path("/other/proj")
    assert p1 == p2 and p1 != p3
    assert p1.startswith("project://")
