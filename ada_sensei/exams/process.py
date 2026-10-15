"""Exam-process scoring: duration and ``/ask`` usage (RQ-EXM-007, RQ-EXM-017).

Both scorers are pure functions of persisted application state, never of model
output (RQ-EXM-031). When the exam defines no limit, the criterion is
``not_evaluated`` and leaves the denominator rather than becoming a pass
(RQ-EXM-017, RQ-EXM-022).
"""

from __future__ import annotations

from datetime import datetime

from ..models import EvaluationCriterion, NotEvaluatedReason
from .models import ExamAttempt, ProcessMetrics
from .rubric import (
    ASK_USAGE_BANDS,
    ASK_USAGE_FLOOR_SCORE,
    DURATION_BANDS,
    DURATION_FLOOR_SCORE,
    PROCESS_DIMENSION,
)

NO_LIMIT = NotEvaluatedReason.no_limit


def duration_score(
    duration_seconds: int | float | None,
    allowed_duration_seconds: int | float | None,
) -> int | None:
    """0-4 band for elapsed time; ``None`` when no limit is defined.

    ``ratio <= 1.00 -> 4``, ``<= 1.10 -> 3``, ``<= 1.25 -> 2``, ``<= 1.50 -> 1``,
    otherwise ``0`` (design.md §Duration scorer).
    """
    if allowed_duration_seconds is None or allowed_duration_seconds <= 0:
        return None
    if duration_seconds is None:
        return None
    ratio = float(duration_seconds) / float(allowed_duration_seconds)
    for threshold, score in DURATION_BANDS:
        if ratio <= threshold + 1e-9:
            return score
    return DURATION_FLOOR_SCORE


def ask_usage_score(
    ask_count: int | None, allowed_ask_count: int | None
) -> int | None:
    """0-4 band for tutor usage; ``None`` when no limit is defined.

    ``ratio <= 0.50 -> 4``, ``<= 1.00 -> 3``, ``<= 1.50 -> 2``, ``<= 2.00 -> 1``,
    otherwise ``0`` (design.md §Ask usage scorer). Usage measures use of the
    tutor, never correctness (spec.md §Exam process scoring).
    """
    if allowed_ask_count is None or allowed_ask_count <= 0:
        return None
    if ask_count is None:
        return None
    ratio = float(ask_count) / float(allowed_ask_count)
    for threshold, score in ASK_USAGE_BANDS:
        if ratio <= threshold + 1e-9:
            return score
    return ASK_USAGE_FLOOR_SCORE


def compute_duration_seconds(
    started_at: datetime | None, finished_at: datetime | None
) -> int | None:
    """Elapsed whole seconds, or ``None`` while the exam is still running."""
    if started_at is None or finished_at is None:
        return None
    return max(0, int((finished_at - started_at).total_seconds()))


def compute_overtime(
    duration_seconds: int | None, allowed_duration_seconds: int | None
) -> int | None:
    """Seconds beyond the allowance; ``None`` when no allowance exists."""
    if duration_seconds is None or allowed_duration_seconds is None:
        return None
    return max(0, int(duration_seconds) - int(allowed_duration_seconds))


def process_metrics(
    attempt: ExamAttempt,
    *,
    duration_weight: float,
    ask_weight: float,
) -> ProcessMetrics:
    """Build the process metrics block from one attempt's persisted state.

    The two weights are required and owned by the caller because the rubric
    definition is the only source of truth for them: defaulting them here would
    let a versioned exam rubric override the ``exam_process`` split and still be
    ignored by the scorer (RQ-EXM-017/018).
    """
    duration = attempt.duration_seconds
    d_score = duration_score(duration, attempt.allowed_duration_seconds)
    a_score = ask_usage_score(attempt.ask_count, attempt.allowed_ask_count)
    d_reason = None if d_score is not None else NO_LIMIT
    a_reason = None if a_score is not None else NO_LIMIT
    return ProcessMetrics(
        started_at=attempt.started_at,
        finished_at=attempt.finished_at,
        duration_seconds=duration,
        allowed_duration_seconds=attempt.allowed_duration_seconds,
        overtime_seconds=compute_overtime(
            duration, attempt.allowed_duration_seconds
        ),
        ask_count=attempt.ask_count,
        allowed_ask_count=attempt.allowed_ask_count,
        duration_score=d_score,
        ask_usage_score=a_score,
        duration_reason=d_reason,
        ask_usage_reason=a_reason,
        criteria=[
            EvaluationCriterion(
                requirement_id=None,
                dimension=PROCESS_DIMENSION,
                weight=duration_weight,
                score=d_score,
                not_evaluated_reason=d_reason,
                note="duration against the allowed exam duration",
            ),
            EvaluationCriterion(
                requirement_id=None,
                dimension=PROCESS_DIMENSION,
                weight=ask_weight,
                score=a_score,
                not_evaluated_reason=a_reason,
                note="/ask usage against the allowed ask count",
            ),
        ],
    )


__all__ = [
    "NO_LIMIT",
    "ask_usage_score",
    "compute_duration_seconds",
    "compute_overtime",
    "duration_score",
    "process_metrics",
]
