"""Tests for PlannerAgent (spec 009)."""
from __future__ import annotations

from pathlib import Path

from ada_sensei.agents.contracts import AgentContext, AgentRole, AgentStatus
from ada_sensei.agents.planner import PlannerAgent
from ada_sensei.learning.stores import (
    LearningEventStore,
    LearningProfileStore,
    MasteryAssessmentStore,
    ProgressionDecisionStore,
)


def _make_planner(tmp_path: Path) -> PlannerAgent:
    return PlannerAgent(
        profile_store=LearningProfileStore(tmp_path),
        event_store=LearningEventStore(tmp_path),
        assessment_store=MasteryAssessmentStore(tmp_path),
        decision_store=ProgressionDecisionStore(tmp_path),
    )


def _ctx(intent: str = "ask", stage_id: str | None = "kotlin-fundamentals") -> AgentContext:
    return AgentContext(
        student_id="student://alice",
        project_id=None,
        intent=intent,
        current_stage_id=stage_id,
        locale="en-US",
    )


def test_planner_returns_ok_status(tmp_path):
    planner = _make_planner(tmp_path)
    result = planner.run(_ctx())
    assert result.status == AgentStatus.OK
    assert result.agent_id == AgentRole.PLANNER


def test_planner_records_learning_event(tmp_path):
    planner = _make_planner(tmp_path)
    store = LearningEventStore(tmp_path)
    planner.run(_ctx("practice"))
    events = store.list_for_student("student://alice")
    assert len(events) >= 1
    assert events[0].student_id == "student://alice"
    assert events[0].event_type == "practice"


def test_planner_progression_decision_none_for_ask(tmp_path):
    """For non-assess intents, no progression decision is created."""
    planner = _make_planner(tmp_path)
    result = planner.run(_ctx("ask"))
    payload = result.structured_payload
    assert payload.progression_decision_ref is None


def test_planner_stage_id_propagated(tmp_path):
    planner = _make_planner(tmp_path)
    result = planner.run(_ctx(stage_id="kotlin-fundamentals"))
    assert result.structured_payload.current_stage_id == "kotlin-fundamentals"


def test_planner_no_stage_returns_ok_with_onboarding_hint(tmp_path):
    planner = _make_planner(tmp_path)
    result = planner.run(_ctx(stage_id=None))
    assert result.status == AgentStatus.OK
    assert result.structured_payload.recommended_next_activity is not None
