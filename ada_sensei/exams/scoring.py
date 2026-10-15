"""Deterministic exam scoring (RQ-EXM-013 to RQ-EXM-022).

``ExamScorer`` supplies the exam-specific dimension scores — clean architecture
and exam process — to the shared ``RubricEngine`` from ``006-evaluate``, which
does the weighting and denominator handling. Nothing here trusts a model:

    raw_score_50   = round(50 × Σ(weight × score / 4) / Σ(weight evaluated))
    suggested_grade = round(1.0 + (raw_score_50 / 50.0) × 4.0, 1)

The full arithmetic is kept in ``ScoreCalculation`` so an instructor can
reconstruct the grade from the report (design.md §PDF integrity).
"""

from __future__ import annotations

import re

from ..evaluation import EvidenceContext, RubricEngine, score_requirement
from ..models import EvaluationCriterion, Evidence, NotEvaluatedReason
from .architecture import ArchitectureReport
from .models import ExamDefinition, ProcessMetrics, ScoreCalculation, ScoreLine
from .process import NO_LIMIT, ask_usage_score, duration_score
from .process import process_metrics as build_process_metrics
from .rubric import (
    ASK_USAGE_CRITERION,
    DURATION_CRITERION,
    EXAM_RUBRIC,
    FUNCTIONAL_DIMENSION,
    PROCESS_DIMENSION,
    RubricDefinition,
)

MAX_SCORE = 4
MAX_RAW_SCORE = 50
MIN_GRADE = 1.0
MAX_GRADE = 5.0

#: Architecture signals observed in project structure, each worth a fraction of
#: the clean-architecture score. Bounded so a large project cannot score higher
#: than a well-layered small one.
ARCHITECTURE_SIGNALS = (
    ("layered packages", 1.0),
    ("viewmodels", 1.0),
    ("repositories", 1.0),
    ("dependency injection", 1.5),
    ("testing structure", 1.0),
    ("domain layer", 1.5),
    ("data layer", 1.0),
    ("navigation", 0.5),
    ("persistence", 0.5),
    ("network boundary", 0.5),
)
ARCHITECTURE_MAX_SIGNALS = sum(weight for _, weight in ARCHITECTURE_SIGNALS)


def suggested_grade(raw_score_50: int | float | None) -> float | None:
    """Map a 0-50 raw score onto 1.0-5.0 (RQ-EXM-021).

    ``round(1.0 + (raw / 50) × 4.0, 1)``: 0 → 1.0, 25 → 3.0, 50 → 5.0.
    """
    if raw_score_50 is None:
        return None
    clamped = min(float(MAX_RAW_SCORE), max(0.0, float(raw_score_50)))
    return round(MIN_GRADE + (clamped / MAX_RAW_SCORE) * (MAX_GRADE - MIN_GRADE), 1)


def architecture_score(report: ArchitectureReport | None) -> tuple[int | None, str]:
    """Deterministic clean-architecture score from observed evidence only.

    Documented and inferred statements never raise this score: only observed
    project structure does (RQ-EXM-014, RQ-EXM-030).
    """
    if report is None or not report.observed:
        return None, "no_evidence"
    observed_text = " ".join(c.claim.lower() for c in report.observed)
    matched = [
        weight for label, weight in ARCHITECTURE_SIGNALS if label in observed_text
    ]
    if not matched:
        return 1, ""
    ratio = sum(matched) / ARCHITECTURE_MAX_SIGNALS
    score = round(ratio * MAX_SCORE)
    return max(0, min(MAX_SCORE, score)), ""


def process_dimension_score(
    metrics: ProcessMetrics,
) -> tuple[float | None, NotEvaluatedReason | None]:
    """Combine the two 50% process subcriteria, renormalizing when one is absent."""
    scored = [c for c in metrics.criteria if c.score is not None]
    if not scored:
        return None, NotEvaluatedReason.no_limit
    total_weight = sum(c.weight for c in scored)
    if total_weight <= 0:
        return None, NotEvaluatedReason.no_limit
    value = sum(c.weight * float(c.score) for c in scored) / total_weight
    return value, None


class ExamScorer:
    """Turns evidence, process metrics and architecture into the exam score."""

    def __init__(
        self,
        definition: RubricDefinition = EXAM_RUBRIC,
        engine: RubricEngine | None = None,
    ) -> None:
        self.definition = definition
        self.engine = engine or RubricEngine(definition)

    # -- process subweights ------------------------------------------------

    def process_weights(self) -> tuple[float, float]:
        """The ``exam_process`` subweights, read from the rubric definition.

        The definition is the only source of truth for the duration/ask split.
        Reading it here means a versioned exam rubric that reweights the split is
        actually honoured, instead of being silently ignored by a hardcoded 50/50
        (RQ-EXM-017/018, ADR-024).
        """
        dimension = self.definition.dimension(PROCESS_DIMENSION)
        declared = {sub.id: sub.weight for sub in dimension.subcriteria}
        if DURATION_CRITERION not in declared or ASK_USAGE_CRITERION not in declared:
            raise ValueError(
                f"rubric {self.definition.ref} must declare the "
                f"{DURATION_CRITERION!r} and {ASK_USAGE_CRITERION!r} subcriteria "
                f"on the {PROCESS_DIMENSION!r} dimension"
            )
        return declared[DURATION_CRITERION], declared[ASK_USAGE_CRITERION]

    # -- criteria ---------------------------------------------------------

    def functional_criteria(
        self, exam: ExamDefinition, evidence: EvidenceContext
    ) -> list[EvaluationCriterion]:
        """One criterion per instructor requirement, weights from the statement.

        RQ-EXM-012: requirement ids and subweights come from the authoritative
        definition, and every criterion carries the evidence backing its score.
        """
        criteria: list[EvaluationCriterion] = []
        for requirement in exam.requirements:
            matched = self._match(requirement.description, evidence.evidence)
            score = score_requirement(
                EvaluationCriterion(
                    requirement_id=requirement.requirement_id, evidence=matched
                )
            )
            criteria.append(
                EvaluationCriterion(
                    requirement_id=requirement.requirement_id,
                    dimension=FUNCTIONAL_DIMENSION,
                    weight=requirement.weight,
                    score=score,
                    evidence=matched,
                    evidence_refs=[e.id for e in matched if e.id],
                    not_evaluated_reason=(
                        None
                        if score is not None
                        else NotEvaluatedReason.no_evidence
                    ),
                    note=requirement.description,
                )
            )
        return criteria

    @staticmethod
    def _match(description: str, evidence: list[Evidence]) -> list[Evidence]:
        """Attach evidence to a requirement using stable path and message keys."""
        keys = _requirement_keys(description)
        if not keys:
            return []
        matched = [
            e
            for e in evidence
            if any(
                key in (e.file or "").lower() or key in e.message.lower()
                for key in keys
            )
        ]
        always = [
            e for e in evidence if e.type in {"compilation", "unit_test"}
        ]
        return [*matched, *always]

    # -- scoring ----------------------------------------------------------

    def score(
        self,
        exam: ExamDefinition,
        evidence: EvidenceContext,
        *,
        attempt=None,
        architecture: ArchitectureReport | None = None,
        build_failed: bool = False,
        extra_limitations: list[str] | None = None,
    ) -> ScoreCalculation:
        """Compute the deterministic exam score and its full calculation table."""
        criteria = self.functional_criteria(exam, evidence)
        duration_weight, ask_weight = self.process_weights()
        metrics = (
            build_process_metrics(
                attempt,
                duration_weight=duration_weight,
                ask_weight=ask_weight,
            )
            if attempt is not None
            else build_process_metrics_from_limits(
                exam,
                duration_weight=duration_weight,
                ask_weight=ask_weight,
            )
        )
        arch_score, arch_note = architecture_score(architecture)

        supplied: dict[str, float | None] = {
            dimension: value.score
            for dimension, value in self.engine.score_dimensions(
                evidence.evidence
            ).items()
        }
        supplied["clean_architecture"] = arch_score
        supplied[PROCESS_DIMENSION] = process_dimension_score(metrics)[0]
        metrics_note = (
            "no allowed duration and no allowed ask count; exam process not evaluated"
            if supplied[PROCESS_DIMENSION] is None
            else ""
        )

        limitations = list(extra_limitations or [])
        if build_failed:
            limitations.append(
                "build failed; compilation-dependent dimensions are not evaluated"
            )
        if arch_score is None:
            limitations.append(
                "clean_architecture: not evaluated (no_evidence)"
            )
        if metrics_note:
            limitations.append(f"exam_process: {metrics_note}")

        breakdown = self.engine.score(
            supplied,
            criteria,
            build_failed=build_failed,
            extra_limitations=limitations,
        )
        return self.calculation(breakdown, metrics, criteria)

    def calculation(
        self,
        breakdown,
        metrics: ProcessMetrics,
        criteria: list[EvaluationCriterion],
    ) -> ScoreCalculation:
        """Assemble the reconstructible calculation table (design.md §PDF)."""
        lines: list[ScoreLine] = []
        for dimension in self.definition.dimensions:
            score = breakdown.dimension_scores.get(dimension.id)
            evaluated = score is not None
            contribution = (
                round(dimension.weight * float(score) / MAX_SCORE * MAX_RAW_SCORE, 3)
                if evaluated
                else None
            )
            reason = breakdown.dimension_reasons.get(dimension.id)
            lines.append(
                ScoreLine(
                    dimension=dimension.id,
                    weight=dimension.weight,
                    score=score,
                    contribution=contribution,
                    not_evaluated_reason=(
                        NotEvaluatedReason(reason) if reason else None
                    ),
                )
            )
        raw = _raw_score(breakdown.weighted_sum, breakdown.weight_denominator)
        return ScoreCalculation(
            rubric_id=breakdown.rubric_id,
            rubric_version=breakdown.rubric_version,
            lines=lines,
            weight_denominator=round(breakdown.weight_denominator, 6),
            weighted_sum=round(breakdown.weighted_sum, 6),
            percentage=breakdown.overall_score,
            raw_score_50=raw,
            max_raw_score=MAX_RAW_SCORE,
            suggested_grade=suggested_grade(raw),
            min_grade=MIN_GRADE,
            max_grade=MAX_GRADE,
        )

    def process_criteria(self, attempt) -> ProcessMetrics:
        duration_weight, ask_weight = self.process_weights()
        return build_process_metrics(
            attempt,
            duration_weight=duration_weight,
            ask_weight=ask_weight,
        )


def _raw_score(weighted_sum: float, denominator: float) -> int | None:
    """``50 × Σ(weight × score / 4) / Σ(weight evaluated)``, rounded to an int."""
    if denominator <= 0:
        return None
    value = MAX_RAW_SCORE * weighted_sum / denominator
    return int(max(0, min(MAX_RAW_SCORE, round(value))))


def build_process_metrics_from_limits(
    exam: ExamDefinition,
    *,
    duration_weight: float,
    ask_weight: float,
) -> ProcessMetrics:
    """Process metrics from the definition alone, before an attempt exists.

    Both criteria stay ``not_evaluated`` while no attempt has run: an exam that
    has not finished has no duration to score (RQ-EXM-017). The weights come from
    the rubric rather than a default, for the same reason as ``process_metrics``.
    """
    d_score = duration_score(None, exam.allowed_duration_seconds)
    a_score = ask_usage_score(0, exam.allowed_ask_count)
    d_reason = None if d_score is not None else NO_LIMIT
    a_reason = None if a_score is not None else NO_LIMIT
    return ProcessMetrics(
        allowed_duration_seconds=exam.allowed_duration_seconds,
        allowed_ask_count=exam.allowed_ask_count,
        ask_count=0,
        duration_score=d_score,
        ask_usage_score=a_score,
        duration_reason=d_reason,
        ask_usage_reason=a_reason,
        criteria=[
            EvaluationCriterion(
                dimension=PROCESS_DIMENSION,
                weight=duration_weight,
                score=d_score,
                not_evaluated_reason=d_reason,
                note="duration against the allowed exam duration",
            ),
            EvaluationCriterion(
                dimension=PROCESS_DIMENSION,
                weight=ask_weight,
                score=a_score,
                not_evaluated_reason=a_reason,
                note="/ask usage against the allowed ask count",
            ),
        ],
    )


def _requirement_keys(description: str) -> set[str]:
    """Content words long enough to be meaningful evidence keys."""
    words = re.findall(r"[a-z0-9]+", description.lower())
    return {w for w in words if len(w) > 3}


__all__ = [
    "ARCHITECTURE_SIGNALS",
    "DURATION_CRITERION",
    "ASK_USAGE_CRITERION",
    "ExamScorer",
    "MAX_GRADE",
    "MAX_RAW_SCORE",
    "MAX_SCORE",
    "MIN_GRADE",
    "architecture_score",
    "build_process_metrics_from_limits",
    "process_dimension_score",
    "suggested_grade",
]
