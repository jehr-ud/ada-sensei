"""Pydantic v2 models for learning path, rubrics, policy, and assessment (spec 008)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator

# ---------------------------------------------------------------------------
# Catalog models
# ---------------------------------------------------------------------------


class StageActions(BaseModel):
    learn: list[str] = []
    practice: list[str] = []
    stage_assessment: list[str] = []


class LearningStage(BaseModel):
    id: str
    number: int
    title: str
    objective: str
    description: str
    prerequisites: list[str] = []
    learning_outcomes: list[str] = []
    key_concepts: list[str] = []
    learning_activities: list[str] = []
    actions: dict[str, list[str]] = {}
    rubric_id: str
    exit_challenge_id: str
    project_generation: dict[str, Any] | None = None


class StageCatalog(BaseModel):
    schema_version: str
    catalog_id: str
    catalog_version: str
    locale: str
    title: str = ""
    description: str = ""
    default_stage_id: str = ""
    stage_order_policy: str = "sequential_with_diagnostic_entry"
    stage_selection_rules: dict[str, Any] = {}
    stages: list[LearningStage]
    cross_stage_rules: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_catalog(self) -> StageCatalog:
        # No duplicate IDs
        ids = [s.id for s in self.stages]
        seen: set[str] = set()
        for sid in ids:
            if sid in seen:
                raise ValueError(f"duplicate stage id: {sid!r}")
            seen.add(sid)
        # All prerequisites reference existing stages
        for stage in self.stages:
            for prereq in stage.prerequisites:
                if prereq not in seen:
                    raise ValueError(
                        f"stage {stage.id!r} references unknown prerequisite {prereq!r}"
                    )
        # Check for cycles using DFS
        adj: dict[str, list[str]] = {s.id: list(s.prerequisites) for s in self.stages}
        visited: set[str] = set()
        in_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            for neighbour in adj.get(node, []):
                if neighbour not in visited:
                    if has_cycle(neighbour):
                        return True
                elif neighbour in in_stack:
                    return True
            in_stack.discard(node)
            return False

        for sid in list(seen):
            if sid not in visited:
                if has_cycle(sid):
                    raise ValueError("prerequisite graph contains a cycle")
        return self


# ---------------------------------------------------------------------------
# Rubric models
# ---------------------------------------------------------------------------


class RubricCriterion(BaseModel):
    id: str
    description: str
    observable_evidence: str = ""
    critical: bool = False
    required_for_decision: bool = True


class RubricDimension(BaseModel):
    id: str
    label: str
    weight: float
    aggregation: str = "arithmetic_mean_of_criterion_scores"
    criteria: list[RubricCriterion]

    @field_validator("weight")
    @classmethod
    def _weight_in_range(cls, v: float) -> float:
        if not 0 < v <= 1.0:
            raise ValueError(f"dimension weight must be in (0, 1], got {v}")
        return v


class StageRubric(BaseModel):
    id: str
    stage_id: str
    stage_number: int
    stage_title: str
    version: str
    scope: str = "stage_exit"
    objective: str = ""
    dimensions: list[RubricDimension]
    exit_challenge: dict[str, Any] = {}
    comprehension_check: list[str] = []
    scoring: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_weights(self) -> StageRubric:
        total = sum(d.weight for d in self.dimensions)
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"rubric {self.id!r} dimension weights sum to {total:.4f}, expected 1.0"
            )
        return self


class RubricCatalog(BaseModel):
    schema_version: str
    catalog_id: str
    catalog_version: str
    locale: str
    score_scale: dict[str, Any] = {}
    dimension_definitions: list[dict[str, Any]] = []
    rubrics: list[StageRubric]

    @model_validator(mode="after")
    def _no_duplicate_rubric_ids(self) -> RubricCatalog:
        seen: set[str] = set()
        for r in self.rubrics:
            if r.id in seen:
                raise ValueError(f"duplicate rubric id: {r.id!r}")
            seen.add(r.id)
        return self


# ---------------------------------------------------------------------------
# Progression policy models
# ---------------------------------------------------------------------------


class DecisionGates(BaseModel):
    minimum_overall_score: float = 3.0
    minimum_each_dimension_score: float = 2.5
    minimum_critical_criterion_score: float = 2.0
    require_all_rubric_criteria_assessed: bool = True
    require_evidence_for_each_dimension: bool = True
    require_exit_challenge: bool = True
    require_comprehension_check: bool = True
    require_reproducible_artifact_or_observation: bool = True
    all_gates_must_pass: bool = True


class ProgressionPolicy(BaseModel):
    policy_id: str
    version: str
    locale: str
    applies_to: str = "stage_exit"
    principle: str = ""
    score_scale: dict[str, Any] = {}
    required_dimensions: dict[str, float]
    decision_gates: DecisionGates
    decision_statuses: dict[str, str] = {}
    evidence_rules: dict[str, Any] = {}
    assessment_procedure: list[str] = []
    retry_policy: dict[str, Any] = {}
    assistance_policy: dict[str, Any] = {}
    progression_rules: dict[str, Any] = {}
    policy_configuration: dict[str, Any] = {}
    assistance_metrics: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_dimension_weights(self) -> ProgressionPolicy:
        total = sum(self.required_dimensions.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"progression policy required_dimensions sum to {total:.4f}, expected 1.0"
            )
        return self


# ---------------------------------------------------------------------------
# Assessment / decision models
# ---------------------------------------------------------------------------


class CriterionResult(BaseModel):
    criterion_id: str
    score: float | None = None  # None = not_evaluated
    not_evaluated_reason: str | None = None
    evidence_refs: list[str] = []


class DimensionResult(BaseModel):
    dimension_id: str
    score: float | None = None  # arithmetic mean of criteria, None if insufficient
    criterion_results: list[CriterionResult] = []
    evidence_refs: list[str] = []


class MasteryAssessment(BaseModel):
    id: str  # URN
    student_id: str
    project_id: str
    stage_id: str
    rubric_id: str
    rubric_version: str
    policy_id: str
    policy_version: str
    catalog_version: str
    challenge_id: str = ""
    dimension_results: list[DimensionResult]
    overall_score: float | None = None
    evidence_refs: list[str] = []
    limitations: list[str] = []
    exit_challenge_completed: bool = False
    comprehension_check_completed: bool = False
    created_at: datetime


class GateResult(BaseModel):
    gate: str
    passed: bool
    reason: str


class ProgressionDecision(BaseModel):
    decision_id: str  # URN
    student_id: str
    from_stage_id: str
    to_stage_id: str | None = None
    status: Literal["READY", "NOT_READY", "INSUFFICIENT_EVIDENCE", "EVALUATION_ERROR"]
    gate_results: list[GateResult] = []
    reasons: list[str] = []
    recommended_activity: str | None = None
    policy_id: str
    policy_version: str
    assessment_id: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Learning profile and events
# ---------------------------------------------------------------------------


class LearningProfile(BaseModel):
    student_id: str
    catalog_id: str
    catalog_version: str
    current_stage_id: str
    mastered_stages: list[str] = []  # stage IDs with READY ProgressionDecision
    diagnostic_completed: bool = False
    selected_locale: str = "en-US"
    created_at: datetime
    updated_at: datetime


class LearningEvent(BaseModel):
    id: str  # URN
    student_id: str
    stage_id: str
    event_type: Literal["study", "practice", "ask", "assess", "progress", "diagnose", "onboard"]
    action: str
    agent_invocation_id: str | None = None
    metadata: dict[str, Any] = {}
    created_at: datetime


__all__ = [
    "CriterionResult",
    "DecisionGates",
    "DimensionResult",
    "GateResult",
    "LearningEvent",
    "LearningProfile",
    "LearningStage",
    "MasteryAssessment",
    "ProgressionDecision",
    "ProgressionPolicy",
    "RubricCatalog",
    "RubricCriterion",
    "RubricDimension",
    "StageCatalog",
    "StageRubric",
]
