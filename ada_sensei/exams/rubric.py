"""The single published rubric consumed by ``/exam`` (RQ-EXM-017/018).

``exam-default:v1`` and ``evaluate-default:v1`` were migrated to
``unified-android:v1`` without compatibility aliases. The exam workflow consumes
the same immutable ``RubricDefinition`` as ``/evaluate``; exam-process metrics
remain informative and never enter the five-dimension score.
"""

from __future__ import annotations

from ..evaluation import (
    UNIFIED_RUBRIC,
    UNIFIED_RUBRIC_REF,
    UNIFIED_RUBRIC_V2,
    UNIFIED_RUBRIC_V2_REF,
    RubricDefinition,
    RubricEngine,
)

#: Functional requirements contribute 40% of the exam, as one dimension whose
#: requirement subweights sum to 1.0 (RQ-EXM-018).
FUNCTIONAL_DIMENSION = "functional_requirements"

#: Exam-process metric identifiers; these are reported, not scored.
PROCESS_DIMENSION = "exam_process"
DURATION_CRITERION = "duration"
ASK_USAGE_CRITERION = "ask_usage"

#: Bands used only for informative process metrics, never for rubric weight.
DURATION_BANDS: tuple[tuple[float, int], ...] = (
    (1.00, 4),
    (1.10, 3),
    (1.25, 2),
    (1.50, 1),
)
DURATION_FLOOR_SCORE = 0

ASK_USAGE_BANDS: tuple[tuple[float, int], ...] = (
    (0.50, 4),
    (1.00, 3),
    (1.50, 2),
    (2.00, 1),
)
ASK_USAGE_FLOOR_SCORE = 0


EXAM_RUBRIC = UNIFIED_RUBRIC_V2


def exam_engine(definition: RubricDefinition = EXAM_RUBRIC) -> RubricEngine:
    """A ``RubricEngine`` bound to the unified rubric (or an override)."""
    return RubricEngine(definition)


def resolve_rubric(rubric_ref: str) -> RubricDefinition:
    """Resolve a published exam rubric; legacy refs stay readable."""
    from .models import ExamDefinitionError

    if rubric_ref == UNIFIED_RUBRIC_V2_REF:
        return UNIFIED_RUBRIC_V2
    if rubric_ref == UNIFIED_RUBRIC_REF:
        return UNIFIED_RUBRIC
    raise ExamDefinitionError(
        "unknown exam rubric "
        f"{rubric_ref!r}; available: {UNIFIED_RUBRIC_V2_REF}, {UNIFIED_RUBRIC_REF}"
    )


__all__ = [
    "ASK_USAGE_BANDS",
    "ASK_USAGE_CRITERION",
    "ASK_USAGE_FLOOR_SCORE",
    "DURATION_BANDS",
    "DURATION_CRITERION",
    "DURATION_FLOOR_SCORE",
    "EXAM_RUBRIC",
    "FUNCTIONAL_DIMENSION",
    "PROCESS_DIMENSION",
    "UNIFIED_RUBRIC_REF",
    "UNIFIED_RUBRIC_V2_REF",
    "exam_engine",
    "resolve_rubric",
]
