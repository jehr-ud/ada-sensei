"""Workflow-neutral contracts shared by every evaluation workflow.

Nothing in this package may import ``cli/`` or ``tui/`` (design.md §9). These
models are what makes the engine reusable: an ``EvidenceContext`` collected by
``/evaluate`` is the same object a different workflow consumes, and a
``RubricDefinition`` is data, not workflow logic (ADR-022, ADR-023).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from ..models import (
    EvaluationCriterion,
    Evidence,
    NotEvaluatedReason,
    UnsupportedClaim,
)
from ..toolchain.models import ToolchainManifest, ToolExecutionEvidence

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


class OverallStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    INCOMPLETE_INFRASTRUCTURE = "INCOMPLETE_INFRASTRUCTURE"


class CriterionStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INFO = "INFO"


NON_EVALUABLE_STATUSES = frozenset(
    {
        CriterionStatus.NOT_EVALUATED,
        CriterionStatus.NOT_CONFIGURED,
        CriterionStatus.NOT_AVAILABLE,
        CriterionStatus.EXECUTION_ERROR,
    }
)


class EvidenceReference(BaseModel):
    evidence_id: str
    type: str
    path: str | None = None
    line: int | None = None
    rule: str | None = None
    summary: str = ""
    command: str | None = None
    tool: str | None = None
    version: str | None = None
    timestamp: datetime | None = None
    artifact_hash: str | None = None


class Finding(BaseModel):
    finding_id: str
    rule_id: str
    severity: str
    message: str
    dimension: str
    status: CriterionStatus = CriterionStatus.INFO
    evidence_ids: list[str] = Field(default_factory=list)
    recommendation_code: str | None = None


class CriterionResult(BaseModel):
    criterion_id: str
    dimension: str
    status: CriterionStatus
    score: float | None = None
    weight: float
    weighted_score: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    analyzer: str
    analyzer_version: str
    rule_version: str

    @model_validator(mode="after")
    def _non_evaluable_has_no_score(self) -> CriterionResult:
        if self.status in NON_EVALUABLE_STATUSES and (
            self.score is not None or self.weighted_score is not None
        ):
            raise ValueError(
                f"{self.criterion_id}: {self.status.value} cannot carry a score"
            )
        return self


class RequirementResult(BaseModel):
    requirement_id: str
    title: str
    description: str
    functional_weight: float
    status: CriterionStatus
    score: float | None = None
    passed_cases: int = 0
    total_cases: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    files_lines: list[str] = Field(default_factory=list)


class TestSummary(BaseModel):
    executed: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    covered_requirements: int = 0
    total_requirements: int = 0
    coverage_ratio: float = 0.0
    coverage_threshold: float = 0.8
    threshold_met: bool = False
    t1_score: float | None = None
    t2_score: float | None = None
    t3_score: float | None = None
    line_coverage_percent: float | None = None


class ToolRun(BaseModel):
    tool_id: str
    name: str
    preparation_status: str
    execution_status: str
    version: str | None = None
    command: str | None = None
    task: str | None = None
    duration_seconds: float | None = None
    output_artifact: str | None = None
    limitation: str | None = None


class AnalyzerCoverage(BaseModel):
    dimension: str
    required_analyzers: list[str] = Field(default_factory=list)
    executed_analyzers: list[str] = Field(default_factory=list)
    not_configured: list[str] = Field(default_factory=list)
    not_available: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    covered_criteria: list[str] = Field(default_factory=list)


class CalculationTraceStep(BaseModel):
    step_id: str
    rule_id: str
    inputs: dict[str, object] = Field(default_factory=dict)
    operation: str
    output: object = None


class Limitation(BaseModel):
    limitation_id: str
    dimension: str
    criterion_id: str | None = None
    tool_state: str | None = None
    reason_code: str
    description: str
    coverage_impact: str
    required_action: str
    analyzer_version: str | None = None
    rule_version: str | None = None


class Observation(BaseModel):
    observation_id: str
    trigger_rule_id: str
    severity: str
    message_template_id: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)


class DimensionResult(BaseModel):
    dimension_id: str
    name: str
    weight: float
    score: float | None = None
    weighted_contribution: float | None = None
    status: CriterionStatus = CriterionStatus.NOT_EVALUATED
    coverage: float = 0.0
    reason_code: str | None = None
    criteria: list[CriterionResult] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    report_id: str
    student_id: str
    project_id: str
    exam_id: str
    attempt_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    locale: str
    rubric_id: str
    rubric_version: str
    overall_status: OverallStatus
    overall_score_5: float | None = None
    overall_score_50: float | None = None
    suggested_grade: float | None = None
    dimension_results: list[DimensionResult] = Field(default_factory=list)
    criterion_results: list[CriterionResult] = Field(default_factory=list)
    requirement_results: list[RequirementResult] = Field(default_factory=list)
    test_summary: TestSummary = Field(default_factory=TestSummary)
    tool_runs: list[ToolRun] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    analyzer_coverage: list[AnalyzerCoverage] = Field(default_factory=list)
    limitations: list[Limitation] = Field(default_factory=list)
    calculation_trace: list[CalculationTraceStep] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    ruleset_versions: dict[str, str] = Field(default_factory=dict)
    toolchain_manifest: ToolchainManifest | None = None
    toolchain_evidence: list[ToolExecutionEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _complete_requires_every_dimension(self) -> EvaluationReport:
        if self.overall_status is OverallStatus.COMPLETE:
            if any(
                d.score is None or d.status in NON_EVALUABLE_STATUSES
                for d in self.dimension_results
            ):
                raise ValueError(
                    "COMPLETE requires every rubric dimension to be evaluated"
                )
            if self.overall_score_5 is None or self.overall_score_50 is None:
                raise ValueError("COMPLETE requires final scores")
        if self.overall_status is OverallStatus.INCOMPLETE_INFRASTRUCTURE and (
            self.overall_score_5 is not None
            or self.overall_score_50 is not None
            or self.suggested_grade is not None
        ):
            raise ValueError("INCOMPLETE_INFRASTRUCTURE cannot carry a final score")
        return self


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
    "AnalyzerCoverage",
    "CalculationTraceStep",
    "CriterionResult",
    "CriterionScore",
    "CriterionStatus",
    "DimensionResult",
    "DimensionScore",
    "EVIDENCE_GROUPS",
    "EvaluationContext",
    "EvaluationExecutionPolicy",
    "EvaluationReport",
    "EvidenceContext",
    "EvidenceReference",
    "Finding",
    "Limitation",
    "NON_EVALUABLE_STATUSES",
    "NotEvaluatedReason",
    "Observation",
    "OverallStatus",
    "ProjectContext",
    "RequirementResult",
    "ScoreBreakdown",
    "TestSummary",
    "ToolRun",
    "UnsupportedClaim",
]
