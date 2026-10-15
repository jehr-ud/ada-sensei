"""``exam-default:v1`` — the exam rubric (RQ-EXM-017, RQ-EXM-018, ADR-024).

The definition is *data* consumed by the shared ``RubricEngine`` from
``006-evaluate``; ``examine`` never instantiates or mutates
``evaluate-default:v1`` (ADR-023, design.md §Rubric engine).
"""

from __future__ import annotations

from ..evaluation import (
    EvidencePolicy,
    RubricDefinition,
    RubricDimension,
    RubricEngine,
    RubricSubcriterion,
)

#: Functional requirements contribute 40% of the exam, as one dimension whose
#: requirement subweights sum to 1.0 (RQ-EXM-018).
FUNCTIONAL_DIMENSION = "functional_requirements"

#: The exam-process dimension, subdivided into two 50% subcriteria.
PROCESS_DIMENSION = "exam_process"
DURATION_CRITERION = "duration"
ASK_USAGE_CRITERION = "ask_usage"

#: The initial bands the spec fixes (design.md §Duration / Ask usage scorers).
#: Exposed as data so an instructor rubric can override them without touching
#: code, and so the tests can assert the published values.
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


EXAM_RUBRIC = RubricDefinition(
    id="exam-default",
    version="v1",
    title="Default Android exam assessment",
    dimensions=(
        RubricDimension(
            id=FUNCTIONAL_DIMENSION,
            weight=0.40,
            description="Instructor functional requirements from the exam statement",
        ),
        RubricDimension(
            id="tests",
            weight=0.15,
            description="Unit-test evidence for the implemented behaviour",
        ),
        RubricDimension(
            id="code_quality",
            weight=0.15,
            description="Detekt findings, duplication, error handling, readability",
        ),
        RubricDimension(
            id="clean_architecture",
            weight=0.15,
            description="Layering, dependency direction, and testability",
        ),
        RubricDimension(
            id="android_practices",
            weight=0.05,
            description="Android Lint and platform practices",
        ),
        RubricDimension(
            id=PROCESS_DIMENSION,
            weight=0.10,
            description="Exam process: duration and /ask usage",
            subcriteria=(
                RubricSubcriterion(
                    id=DURATION_CRITERION,
                    weight=0.50,
                    description="Time taken against the allowed duration",
                ),
                RubricSubcriterion(
                    id=ASK_USAGE_CRITERION,
                    weight=0.50,
                    description="/ask invocations against the allowed count",
                ),
            ),
        ),
    ),
    evidence_policy=EvidencePolicy(
        renormalize=True,
        allow_empty_score=False,
        build_dependent=(FUNCTIONAL_DIMENSION, "clean_architecture"),
        not_evaluated_label="not evaluated",
    ),
    functional_dimension=FUNCTIONAL_DIMENSION,
)


def exam_engine(definition: RubricDefinition = EXAM_RUBRIC) -> RubricEngine:
    """A ``RubricEngine`` bound to the exam rubric (or an override)."""
    return RubricEngine(definition)


def resolve_rubric(rubric_ref: str) -> RubricDefinition:
    """Resolve a ``<id>:<version>`` reference to a known definition.

    An instructor may point an exam at a different versioned rubric; an unknown
    reference is an error rather than a silent fallback to the default.
    """
    from .models import ExamDefinitionError

    if rubric_ref == EXAM_RUBRIC.ref:
        return EXAM_RUBRIC
    raise ExamDefinitionError(
        f"unknown exam rubric {rubric_ref!r}; available: {EXAM_RUBRIC.ref}"
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
    "exam_engine",
    "resolve_rubric",
]
