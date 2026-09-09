from __future__ import annotations

from ada_sensei.models import EvaluationResult
from ada_sensei.storage.results import ResultStore


def test_roundtrip(tmp_path):
    store = ResultStore(str(tmp_path))
    result = EvaluationResult(
        attempt_id="attempt://a",
        exercise_id="exercise://e",
        student_id="student://s",
        overall_score=90.0,
    )
    store.save(result)
    loaded = store.get(result.id)
    assert loaded is not None
    assert loaded.id == result.id
    assert loaded.overall_score == 90.0
    assert store.get("result://missing") is None
