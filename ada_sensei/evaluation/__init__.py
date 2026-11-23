"""Reusable evaluation infrastructure owned by ``006-evaluate``.

This package is the evaluation engine boundary described in ADR-022: evidence
collection, requirement matching, rubric mechanics, and structured
interpretation. It is deliberately independent of ``/evaluate`` so a higher-level
workflow such as ``007-examine`` can reuse it with its own rubric definition
(ADR-023, RQ-EVA-036).

Nothing here may import ``ada_sensei.cli`` or ``ada_sensei.cli.tui``.
"""

from .agent import (
    EvaluationAgent,
    EvaluationInterpretation,
    GroundedClaim,
    GroundedInterpretation,
    unavailable_interpretation,
)
from .engine import (
    NO_EXERCISE_LIMITATION,
    EvaluationEngine,
    evidence_reference_table,
    unsupported_claim_summary,
)
from .evidence import (
    AndroidProjectAnalyzer,
    EvidenceCollector,
    GradleTool,
    StaticAnalysisTool,
    TestTool,
    assign_evidence_ids,
)
from .exam_agent import EvaluatorAgent
from .matcher import RequirementMatch, RequirementMatcher
from .models import (
    NON_EVALUABLE_STATUSES,
    AnalyzerCoverage,
    CalculationTraceStep,
    CriterionResult,
    CriterionScore,
    CriterionStatus,
    DimensionResult,
    DimensionScore,
    EvaluationContext,
    EvaluationExecutionPolicy,
    EvaluationReport,
    EvidenceContext,
    EvidenceReference,
    Finding,
    Limitation,
    Observation,
    OverallStatus,
    ProjectContext,
    RequirementResult,
    ScoreBreakdown,
    TestSummary,
    ToolRun,
)
from .preflight import ProjectIssue, ProjectPreflight, ProjectReadiness
from .rubric import (
    EVALUATE_RUBRIC,
    LEGACY_RUBRIC_REFS,
    SEVERITIES,
    UNIFIED_RUBRIC,
    UNIFIED_RUBRIC_REF,
    DimensionScorer,
    EvidencePolicy,
    RubricDefinition,
    RubricDimension,
    RubricEngine,
    RubricSubcriterion,
    evaluate_engine,
    normalize_rubric_ref,
    score_requirement,
)

__all__ = [
    "AndroidProjectAnalyzer",
    "AnalyzerCoverage",
    "CalculationTraceStep",
    "CriterionResult",
    "CriterionScore",
    "CriterionStatus",
    "DimensionResult",
    "DimensionScore",
    "DimensionScorer",
    "EVALUATE_RUBRIC",
    "EvaluationAgent",
    "EvaluatorAgent",
    "EvaluationContext",
    "EvaluationEngine",
    "EvaluationExecutionPolicy",
    "EvaluationInterpretation",
    "EvaluationReport",
    "EvidenceCollector",
    "EvidenceContext",
    "EvidencePolicy",
    "EvidenceReference",
    "Finding",
    "GradleTool",
    "LEGACY_RUBRIC_REFS",
    "GroundedClaim",
    "GroundedInterpretation",
    "Limitation",
    "NON_EVALUABLE_STATUSES",
    "NO_EXERCISE_LIMITATION",
    "Observation",
    "OverallStatus",
    "ProjectContext",
    "RequirementResult",
    "ProjectIssue",
    "ProjectPreflight",
    "ProjectReadiness",
    "RequirementMatch",
    "RequirementMatcher",
    "RubricDefinition",
    "RubricDimension",
    "RubricEngine",
    "RubricSubcriterion",
    "SEVERITIES",
    "ScoreBreakdown",
    "StaticAnalysisTool",
    "TestSummary",
    "TestTool",
    "ToolRun",
    "UNIFIED_RUBRIC",
    "UNIFIED_RUBRIC_REF",
    "assign_evidence_ids",
    "evaluate_engine",
    "normalize_rubric_ref",
    "evidence_reference_table",
    "score_requirement",
    "unavailable_interpretation",
    "unsupported_claim_summary",
]
