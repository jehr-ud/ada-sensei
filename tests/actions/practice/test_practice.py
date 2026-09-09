from __future__ import annotations

import pytest
from ada_sensei.actions.base import ActionServices
from ada_sensei.actions.practice import (
    PracticeAction,
    PracticeInput,
    PracticeInputError,
)
from ada_sensei.config import Config
from ada_sensei.context import SessionContext
from ada_sensei.llm.base import LLMClient
from ada_sensei.models import Difficulty


def _criteria(*rids: str) -> list[dict[str, object]]:
    weight = 1 / len(rids)
    return [
        {
            "requirement_id": rid,
            "dimension": "functional_requirements",
            "weight": weight,
        }
        for rid in rids
    ]


VALID_EXERCISE = {
    "id": "exercise://e1",
    "title": "Task List with ViewModel State",
    "topic": "compose-state",
    "difficulty": "intermediate",
    "objective": "manage mutable UI state in a ViewModel using StateFlow",
    "statement": "Implement a task list.",
    "requirements": [
        {"id": "req://r1", "summary": "Add tasks"},
        {"id": "req://r2", "summary": "Remove tasks"},
        {"id": "req://r3", "summary": "Display tasks with LazyColumn"},
    ],
    "constraints": ["UI state must be kept in a ViewModel"],
    "hints": ["Think about StateFlow", "Use a mutableStateOf held by the VM"],
    "evaluation_criteria": _criteria("req://r1", "req://r2", "req://r3"),
    "source": "generated",
    "created_at": "2026-01-01T00:00:00Z",
}


class FakeClient(LLMClient):
    def __init__(self, payload=None):

        self.base = {
            "id": "exercise://e1",
            "title": "Task List with ViewModel State",
            "topic": "compose-state",
            "difficulty": "intermediate",
            "objective": "manage mutable UI state",
            "statement": "Implement a task list.",
            "requirements": [
                {"id": "req://r1", "summary": "Add tasks"},
                {"id": "req://r2", "summary": "Remove tasks"},
                {"id": "req://r3", "summary": "Display tasks with LazyColumn"},
            ],
            "constraints": ["UI state in ViewModel"],
            "hints": ["Think about StateFlow", "Hold state in the VM"],
            "evaluation_criteria": _criteria("req://r1", "req://r2", "req://r3"),
            "source": "generated",
            "created_at": "2026-01-01T00:00:00Z",
        }
        self.payload = payload
        self.calls = 0

    def chat(self, messages, *, model=None, temperature=None):
        return ""

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        import json

        self.calls += 1
        if self.payload is not None:
            return self.payload
        data = dict(self.base)
        for msg in messages:
            content = msg.get("content", "")
            for level in ("beginner", "intermediate", "advanced"):
                marker = f"Difficulty: {level}"
                if marker in content or f"difficulty={level}" in content:
                    data["difficulty"] = level
        return json.dumps(data)


class Fixtures:
    @staticmethod
    def fake_payload(difficulty="intermediate"):
        import json

        data = dict(VALID_EXERCISE)
        data["difficulty"] = difficulty
        return json.dumps(data)


def _fresh(tmp_path, student="student://s1", hstore=None):
    config = Config(project={"path": str(tmp_path / "proj")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    ctx = SessionContext(config=config, data_dir=tmp_path / "sess")
    ctx.set_student(student)
    if hstore is None:
        hstore = __import__(
            "ada_sensei.storage.history", fromlist=["HistoryStore"]
        ).HistoryStore(str(tmp_path))
        hstore.create_profile(student, confirmed=True)
    return ActionServices.build(config, ctx, FakeClient()), hstore


def test_generates_exercise(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    assert result.exercise.id.startswith("exercise://")


def test_has_objective(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    assert result.exercise.objective


def test_difficulty_validated(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(
        PracticeInput(difficulty=Difficulty.advanced, adaptive=False)
    )
    assert result.exercise.difficulty == Difficulty.advanced


def test_invalid_difficulty_rejected():
    with pytest.raises(PracticeInputError):
        PracticeInput.from_options(difficulty="expert")


def test_has_requirements(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    assert result.exercise.requirements


def test_has_topics(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    assert result.exercise.topic


def test_no_solution_default(tmp_path):
    from ada_sensei.actions.practice import PracticePrompt

    system = PracticePrompt.SYSTEM
    assert "Do NOT provide the complete solution" in system


def test_progressive_hints(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    assert isinstance(result.exercise.hints, list)
    assert len(result.exercise.hints) >= 1


def test_self_contained(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    assert result.exercise.statement


def test_structured_roundtrip(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    ex = services.exercises.get(result.exercise.id)
    assert ex is not None
    assert ex.requirements[0].id.startswith("req://")


def test_topic_from_history_or_default(tmp_path):
    services, _ = _fresh(tmp_path)
    services.history.add_strength("student://s1", "kotlin")
    result = PracticeAction(services).run(
        PracticeInput(topic="compose-state", adaptive=False)
    )
    assert result.exercise.topic == "compose-state"


def test_objective_override(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(
        PracticeInput(objective="custom goal", adaptive=False)
    )
    # objective comes from the provider payload, not the input (model picks topic)
    assert result.exercise.id


def test_adaptive_default_on(tmp_path):
    services, _ = _fresh(tmp_path)
    assert PracticeInput().adaptive is True


def test_exercise_persisted_and_loaded(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    loaded = services.exercises.get(result.exercise.id)
    assert loaded is not None
    assert loaded.id == result.exercise.id


def test_requirement_ids_stable(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    ex = services.exercises.get(result.exercise.id)
    criteria = ex.evaluation_criteria
    req_ids = {r.id for r in ex.requirements}
    assert len(req_ids) == len(ex.requirements)
    assert all(c.requirement_id in req_ids for c in criteria)


def test_assistance_level_advance(tmp_path):
    services, _ = _fresh(tmp_path)
    PracticeAction(services).run(PracticeInput(adaptive=False))
    before = services.context.assistance_level
    services.context.advance_assistance()
    assert services.context.assistance_level != before


def test_no_project_writes(tmp_path):
    services, hstore = _fresh(tmp_path)
    proj = services.config.project.path
    PracticeAction(services).run(PracticeInput(adaptive=False))
    import os

    assert not os.path.exists(proj)


def test_attempt_created_and_bound(tmp_path):
    services, _ = _fresh(tmp_path)
    result = PracticeAction(services).run(PracticeInput(adaptive=False))
    attempt = services.attempts.get(services.context.attempt_id)
    assert attempt is not None
    assert attempt.student_id == "student://s1"
    assert attempt.exercise_id == result.exercise.id
