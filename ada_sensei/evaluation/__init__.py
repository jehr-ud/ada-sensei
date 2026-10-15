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
from .matcher import RequirementMatch, RequirementMatcher
from .models import (
    CriterionScore,
    DimensionScore,
    EvaluationContext,
    EvaluationExecutionPolicy,
    EvidenceContext,
    ProjectContext,
    ScoreBreakdown,
)
from .rubric import (
    EVALUATE_RUBRIC,
    SEVERITIES,
    DimensionScorer,
    EvidencePolicy,
    RubricDefinition,
    RubricDimension,
    RubricEngine,
    RubricSubcriterion,
    evaluate_engine,
    score_requirement,
)

__all__ = [
    "AndroidProjectAnalyzer",
    "CriterionScore",
    "DimensionScore",
    "DimensionScorer",
    "EVALUATE_RUBRIC",
    "EvaluationAgent",
    "EvaluationContext",
    "EvaluationEngine",
    "EvaluationExecutionPolicy",
    "EvaluationInterpretation",
    "EvidenceCollector",
    "EvidenceContext",
    "EvidencePolicy",
    "GradleTool",
    "GroundedClaim",
    "GroundedInterpretation",
    "NO_EXERCISE_LIMITATION",
    "ProjectContext",
    "RequirementMatch",
    "RequirementMatcher",
    "RubricDefinition",
    "RubricDimension",
    "RubricEngine",
    "RubricSubcriterion",
    "SEVERITIES",
    "ScoreBreakdown",
    "StaticAnalysisTool",
    "TestTool",
    "assign_evidence_ids",
    "evaluate_engine",
    "evidence_reference_table",
    "score_requirement",
    "unavailable_interpretation",
    "unsupported_claim_summary",
]
