"""Workflow-neutral contracts shared by every evaluation workflow.

Nothing in this package may import ``cli/`` or ``tui/`` (design.md §9). These
models are what makes the engine reusable: an ``EvidenceContext`` collected by
``/evaluate`` is the same object a different workflow consumes, and a
``RubricDefinition`` is data, not workflow logic (ADR-022, ADR-023).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..models import (
    EvaluationCriterion,
    Evidence,
    NotEvaluatedReason,
    UnsupportedClaim,
)

#: Evidence groups a workflow-neutral context always carries (design.md §2).
EVIDENCE_GROUPS = (
    "project",
    "build",
    "test",
    "lint",
    "detekt",
    "structure",
    "unit_test",
    "compilation",
    "android_lint",
)


class EvidenceContext(BaseModel):
    """Deterministic evidence plus its provenance, independent of any workflow.

    RQ-EVA-029: represented separately from ``/evaluate`` so another workflow
    can consume the same evidence without duplicating Android analysis or tool
    execution. Every item carries an ``ev://<n>`` id so LLM claims can cite it
    (RQ-EVA-035).
    """

    project_id: str | None = None
    project_path: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    matched_requirements: list[EvaluationCriterion] = Field(default_factory=list)
    #: Evidence no requirement claimed; preserved, never dropped (RQ-EVA-005).
    unmatched_evidence: list[str] = Field(default_factory=list)
    collected_at_commands: list[str] = Field(default_factory=list)

    def all_evidence(self) -> list[Evidence]:
        return list(self.evidence)

    def by_group(self, *groups: str) -> list[Evidence]:
        """Evidence whose ``type`` is in ``groups``."""
        wanted = set(groups)
        return [e for e in self.evidence if e.type in wanted]

    def by_source(self, *sources: str) -> list[Evidence]:
        wanted = set(sources)
        return [e for e in self.evidence if e.source in wanted]

    def ids(self) -> set[str]:
        return {e.id for e in self.evidence if e.id}

    def limitation_texts(self) -> list[str]:
        return list(self.limitations)

    def has_group(self, *groups: str) -> bool:
        return bool(self.by_group(*groups))


class EvaluationExecutionPolicy(BaseModel):
    """Whether Gradle-based tools may run, and how much of them to run.

    RQ-EVA-020 fixes the default scope; RQ-EVA-021 forbids
    ``connectedAndroidTest``; RQ-EVA-019/023 make the policy the single place
    where confirmation and ``--yes`` are resolved.
    """

    gradle_confirmed: bool = False
    run_build: bool = True
    run_unit_tests: bool = True
    run_lint: bool = True
    run_detekt: bool = True
    run_instrumented: bool = False
    timeout_seconds: int | None = None

    def gradle_requested(self) -> bool:
        return any(
            (
                self.run_build,
                self.run_unit_tests,
                self.run_lint,
                self.run_detekt,
                self.run_instrumented,
            )
        )

    def blocked_reason(self) -> str | None:
        if self.run_instrumented:
            return (
                "connectedAndroidTest is reserved for a future option and is "
                "not supported now"
            )
        if self.gradle_requested() and not self.gradle_confirmed:
            return (
                "confirmation required before executing Gradle tasks; use "
                "interactive confirmation or --yes"
            )
        return None


class CriterionScore(BaseModel):
    """A single scored criterion handed to the rubric engine."""

    criterion_id: str
    dimension: str
    score: int | None = None
    weight: float = 1.0
    not_evaluated_reason: NotEvaluatedReason | None = None
    note: str = ""


class DimensionScore(BaseModel):
    """A dimension's resolved score and the denominator policy behind it."""

    dimension: str
    weight: float
    score: float | None = None
    not_evaluated_reason: NotEvaluatedReason | None = None
    note: str = ""


class ScoreBreakdown(BaseModel):
    """Deterministic scoring output (design.md §2 ``RubricEngine``)."""

    rubric_id: str
    rubric_version: str
    overall_score: float | None = None
    dimension_scores: dict[str, float | None] = Field(default_factory=dict)
    evaluated_dimensions: list[str] = Field(default_factory=list)
    not_evaluated_dimensions: list[str] = Field(default_factory=list)
    #: Why each dimension was left unevaluated, so a report can show the reason
    #: without re-deriving it from the limitation strings.
    dimension_reasons: dict[str, str] = Field(default_factory=dict)
    weighted_sum: float = 0.0
    weight_denominator: float = 0.0
    functional_subweight_sum: float | None = None
    limitations: list[str] = Field(default_factory=list)
    criteria: list[EvaluationCriterion] = Field(default_factory=list)


class ProjectContext(BaseModel):
    """Read-only handle to the project under evaluation (RQ-EVA-001)."""

    path: str
    project_id: str | None = None

    @classmethod
    def from_path(cls, path: str | Path) -> ProjectContext:
        from ..urns import URN

        resolved = str(Path(path).expanduser().resolve())
        return cls(path=resolved, project_id=URN.project_id_from_path(resolved))


class EvaluationContext(BaseModel):
    """Identity and interpretation settings for one evaluation run.

    Deliberately data-only: an ``LLMClient`` is passed to the engine as a
    separate argument so this model stays serializable and the engine stays
    free of provider concerns.
    """

    student_id: str | None = None
    attempt_id: str | None = None
    exercise_id: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = None
    max_attempts: int = 3


__all__ = [
    "CriterionScore",
    "DimensionScore",
    "EVIDENCE_GROUPS",
    "EvaluationContext",
    "EvaluationExecutionPolicy",
    "EvidenceContext",
    "NotEvaluatedReason",
    "ProjectContext",
    "ScoreBreakdown",
    "UnsupportedClaim",
]
