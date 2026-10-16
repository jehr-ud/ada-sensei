"""Autonomous agent orchestration: TeacherAgent + PlannerAgent + EvaluatorAgent + TrainerAgent."""
from __future__ import annotations

from .contracts import (
    AgentContext,
    AgentInvocationRecord,
    AgentRole,
    AgentStatus,
    EvaluatorPayload,
    PlannerPayload,
    SpecialistResult,
    TeacherDecision,
    TrainerPayload,
)
from .evaluator import EvaluatorAgent
from .planner import PlannerAgent
from .stores import AgentInvocationStore
from .teacher import TeacherAgent
from .trainer import TrainerAgent

__all__ = [
    "AgentContext",
    "AgentInvocationRecord",
    "AgentInvocationStore",
    "AgentRole",
    "AgentStatus",
    "EvaluatorAgent",
    "EvaluatorPayload",
    "PlannerAgent",
    "PlannerPayload",
    "SpecialistResult",
    "TeacherAgent",
    "TeacherDecision",
    "TrainerAgent",
    "TrainerPayload",
]
