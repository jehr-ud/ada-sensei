from __future__ import annotations

from ada_sensei.models import Exercise
from ada_sensei.storage.exercises import ExerciseStore


def test_get_by_id(tmp_path):
    store = ExerciseStore(str(tmp_path))
    exercise = Exercise(title="t", statement="s")
    store.save(exercise)
    loaded = store.get(exercise.id)
    assert loaded is not None
    assert loaded.id == exercise.id
    assert loaded.title == "t"
    assert store.get("exercise://missing") is None
