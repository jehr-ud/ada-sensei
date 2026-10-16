"""Typed input/output contracts for all agents (spec 009-agent-orchestration)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AgentRole(StrEnum):
    TEACHER = "teacher"
    PLANNER = "planner"
    EVALUATOR = "evaluator"
    TRAINER = "trainer"


class AgentStatus(StrEnum):
    OK = "ok"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    FAILED = "failed"


@dataclass
class AgentContext:
    """
    Minimal context passed to each specialist.
    Never includes full raw conversation history — only bounded summaries.
    """

    student_id: str
    project_id: str | None
    intent: str  # "ask", "practice", "evaluate", "exam_init", "exam_finish", "learn", "diagnose"
    current_stage_id: str | None
    locale: str
    fallback_locale: str = "en-US"
    #: Localized stage objective for stage-aware responses (spec 0011 §4);
    #: ``None`` when the stage or catalog is unavailable — never invented.
    stage_objective: str | None = None
    assistance_level: str = "guiding_question"
    recent_summary: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    action_input: Any = None  # the original command/request


@dataclass
class PlannerPayload:
    current_stage_id: str | None
    recommended_next_activity: str | None
    mastery_gaps: list[str]
    progression_decision_ref: str | None  # decision_id or None
    learning_event_id: str | None


@dataclass
class EvaluatorPayload:
    diagnostic_signal: str | None  # brief misconception/gap, or None
    assessment_result_ref: str | None  # assessment id, or None
    criterion_gaps: list[str]
    limitations: list[str]


@dataclass
class TrainerPayload:
    explanation: str
    practice_task: str | None
    hints: list[str]
    recommended_resources: list[str]


@dataclass
class SpecialistResult:
    agent_id: AgentRole
    invocation_id: str
    status: AgentStatus
    summary: str
    structured_payload: PlannerPayload | EvaluatorPayload | TrainerPayload
    evidence_refs: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    recommended_next_step: str | None = None


@dataclass
class TeacherDecision:
    """Final output from TeacherAgent for one student-facing action."""

    action_result: Any  # typed result from the existing action service
    specialist_results: list[SpecialistResult]
    progression_decision_ref: str | None  # decision_id if a progression was recorded
    final_response: str
    limitations: list[str] = field(default_factory=list)
    locale: str = "en-US"
    invocation_id: str = ""


@dataclass
class AgentInvocationRecord:
    """Persisted record for observability and testing."""

    id: str
    student_id: str
    intent: str
    action: str
    specialist_results: list[dict[str, Any]]
    action_result_type: str
    locale: str
    model: str
    status: str
    created_at: datetime
    duration_ms: int = 0
    limitations: list[str] = field(default_factory=list)


__all__ = [
    "AgentContext",
    "AgentInvocationRecord",
    "AgentRole",
    "AgentStatus",
    "EvaluatorPayload",
    "PlannerPayload",
    "SpecialistResult",
    "TeacherDecision",
    "TrainerPayload",
]
