"""RQ-EXM-017: process criterion bands and not-evaluated handling."""

from __future__ import annotations

from ada_sensei.exams.process import (
    ask_usage_score,
    compute_duration_seconds,
    compute_overtime,
    duration_score,
    process_metrics,
)
from ada_sensei.models import NotEvaluatedReason
from exams_helpers import make_attempt


def test_bands_and_not_evaluated():
    assert duration_score(0, 3600) == 4
    assert duration_score(3600, 3600) == 4
    assert duration_score(3960, 3600) == 3
    assert duration_score(4500, 3600) == 2
    assert duration_score(5400, 3600) == 1
    assert duration_score(5500, 3600) == 0
    assert duration_score(None, 3600) is None
    assert duration_score(100, None) is None

    assert ask_usage_score(0, 4) == 4
    assert ask_usage_score(2, 4) == 4
    assert ask_usage_score(4, 4) == 3
    assert ask_usage_score(6, 4) == 2
    assert ask_usage_score(8, 4) == 1
    assert ask_usage_score(9, 4) == 0
    assert ask_usage_score(2, None) is None

    assert compute_duration_seconds(None, None) is None
    assert compute_overtime(100, 60) == 40
    assert compute_overtime(50, 60) == 0


def test_process_metrics_no_limit_not_evaluated():
    attempt = make_attempt(
        allowed_duration_seconds=None,
        allowed_ask_count=None,
        ask_count=3,
        duration_seconds=120,
    )
    metrics = process_metrics(attempt, duration_weight=0.5, ask_weight=0.5)
    assert metrics.duration_score is None
    assert metrics.ask_usage_score is None
    assert metrics.duration_reason is NotEvaluatedReason.no_limit
    assert metrics.ask_usage_reason is NotEvaluatedReason.no_limit
    assert all(c.score is None for c in metrics.criteria)
    assert all(
        c.not_evaluated_reason is NotEvaluatedReason.no_limit for c in metrics.criteria
    )