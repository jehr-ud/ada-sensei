"""Rubric mechanics separated from rubric definitions (ADR-023).

``RubricDefinition`` is versioned *data*: ids, dimensions, weights, subcriteria,
score scale, and the evidence policy. ``RubricEngine`` is stateless mechanics
that consume any validated definition. ``/evaluate`` ships ``evaluate-default:v1``
and no other workflow may mutate it; ``007-examine`` ships its own
``exam-default:v1`` against the same engine.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from ..models import EvaluationCriterion, Evidence, NotEvaluatedReason
from .models import (
    CriterionScore,
    DimensionScore,
    ScoreBreakdown,
)

#: Weight tolerance for the ``== 1.0`` sum checks.
WEIGHT_EPSILON = 1e-9
SUBWEIGHT_EPSILON = 1e-6

#: The only criterion score range the 0-100 normalization accepts.
MIN_SCORE = 0
MAX_SCORE = 4

#: Static-analysis severities preserved from lint/detekt (RQ-EVA-015).
SEVERITIES = ("error", "warning", "info")


class RubricSubcriterion(BaseModel):
    """A weight inside one dimension, normalized against its siblings."""

    model_config = ConfigDict(frozen=True)

    id: str
    weight: float
    description: str = ""

    @model_validator(mode="after")
    def _weight_in_range(self) -> RubricSubcriterion:
        if self.weight < 0:
            raise ValueError(f"subcriterion {self.id!r} weight must be >= 0")
        return self


class RubricDimension(BaseModel):
    """One weighted scoring dimension."""

    model_config = ConfigDict(frozen=True)

    id: str
    weight: float
    description: str = ""
    subcriteria: tuple[RubricSubcriterion, ...] = ()

    @model_validator(mode="after")
    def _validate(self) -> RubricDimension:
        if self.weight < 0:
            raise ValueError(f"dimension {self.id!r} weight must be >= 0")
        ids = [s.id for s in self.subcriteria]
        if len(ids) != len(set(ids)):
            raise ValueError(
                f"dimension {self.id!r} has duplicate subcriterion ids: {ids}"
            )
        if self.subcriteria:
            total = sum(s.weight for s in self.subcriteria)
            if abs(total - 1.0) > SUBWEIGHT_EPSILON:
                raise ValueError(
                    f"dimension {self.id!r} subcriterion weights must sum to 1.0, "
                    f"got {total}"
                )
        return self


class EvidencePolicy(BaseModel):
    """How the engine treats criteria and dimensions without evidence.

    RQ-EVA-014 / ADR-011: a criterion without evidence is ``not_evaluated``, never
    assumed to pass or fail, and is excluded from the score denominator.
    """

    model_config = ConfigDict(frozen=True)

    #: Exclude not-evaluated dimensions from the score denominator.
    renormalize: bool = True
    #: Refuse to score when nothing at all could be evaluated.
    allow_empty_score: bool = False
    #: Dimensions that are compilation-dependent are not evaluated after a
    #: build failure (RQ-EVA-018).
    build_dependent: tuple[str, ...] = ("functional_requirements",)
    not_evaluated_label: str = "not evaluated"


class RubricDefinition(BaseModel):
    """A versioned rubric: id, dimensions, weights, scale, evidence policy."""

    model_config = ConfigDict(frozen=True)

    id: str
    version: str
    title: str = ""
    dimensions: tuple[RubricDimension, ...]
    score_scale_max: int = MAX_SCORE
    evidence_policy: EvidencePolicy = EvidencePolicy()
    #: Dimension whose subcriteria subdivide an exercise's functional
    #: requirements; its subweights never add top-level weight (RQ-EVA-024).
    functional_dimension: str = "functional_requirements"

    @model_validator(mode="after")
    def _validate(self) -> RubricDefinition:
        if not self.dimensions:
            raise ValueError("a rubric definition needs at least one dimension")
        ids = [d.id for d in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate dimension ids: {ids}")
        if self.score_scale_max != MAX_SCORE:
            raise ValueError(
                f"score scale max must be {MAX_SCORE}, got {self.score_scale_max}"
            )
        if self.functional_dimension not in ids:
            raise ValueError(
                f"functional_dimension {self.functional_dimension!r} is not a "
                f"declared dimension: {ids}"
            )
        self.validate_weights()
        return self

    # -- derived views ---------------------------------------------------

    @property
    def ref(self) -> str:
        """``<id>:<version>`` — the value persisted on results and reports."""
        return f"{self.id}:{self.version}"

    @property
    def dimension_ids(self) -> list[str]:
        return [d.id for d in self.dimensions]

    def dimension(self, dimension_id: str) -> RubricDimension:
        for dim in self.dimensions:
            if dim.id == dimension_id:
                return dim
        raise KeyError(
            f"unknown dimension {dimension_id!r} in rubric {self.ref}; "
            f"declared: {self.dimension_ids}"
        )

    def weight_of(self, dimension_id: str) -> float:
        return self.dimension(dimension_id).weight

    def weights(self) -> dict[str, float]:
        return {d.id: d.weight for d in self.dimensions}

    # -- validation ------------------------------------------------------

    def validate_weights(self) -> None:
        total = sum(d.weight for d in self.dimensions)
        if abs(total - 1.0) > WEIGHT_EPSILON:
            raise ValueError(
                f"top-level weights must sum to 1.0, got {total} "
                f"({self.ref})"
            )

    def validate_subweights(self, subweights: dict[str, float]) -> None:
        """Validate explicit subweights that subdivide a dimension.

        Only called when subweights are actually supplied; the rubric's declared
        subcriteria are validated by the model itself.
        """
        if not subweights:
            return
        total = sum(subweights.values())
        if abs(total - 1.0) > SUBWEIGHT_EPSILON:
            raise ValueError(
                f"{self.functional_dimension} subweights must sum to 1.0, "
                f"got {total}"
            )


#: ``evaluate-default:v1`` — the ``/evaluate`` rubric (RQ-EVA-022, ADR-017).
EVALUATE_RUBRIC = RubricDefinition(
    id="evaluate-default",
    version="v1",
    title="Default exercise/project evaluation",
    dimensions=(
        RubricDimension(
            id="functional_requirements",
            weight=0.40,
            description="Exercise functional requirements",
            subcriteria=(),
        ),
        RubricDimension(
            id="tests",
            weight=0.20,
            description="Unit-test evidence and coverage of behaviour",
        ),
        RubricDimension(
            id="code_quality",
            weight=0.15,
            description="Detekt and source-quality findings",
        ),
        RubricDimension(
            id="architecture",
            weight=0.15,
            description="Structure, layering, and boundaries",
        ),
        RubricDimension(
            id="android_practices",
            weight=0.10,
            description="Android Lint and platform practices",
        ),
    ),
)


class DimensionScorer:
    """Deterministic per-dimension scoring rules for a rubric definition.

    These are *rules*, not a workflow: they turn collected evidence into a 0-4
    score or ``None`` when evidence is insufficient. Each rule is overridable so
    a different rubric can express its own dimension without reimplementing the
    normalization in :class:`RubricEngine`.
    """

    def __init__(self, definition: RubricDefinition) -> None:
        self.definition = definition
        self._rules = {
            "tests": self._score_tests,
            "code_quality": self._score_static_quality,
            "android_practices": self._score_static_practices,
            "architecture": self._score_architecture,
        }

    def score(
        self, dimension: str, evidence: list[Evidence]
    ) -> tuple[int | None, NotEvaluatedReason | None]:
        rule = self._rules.get(dimension)
        if rule is None:
            return None, NotEvaluatedReason.no_evidence
        return rule(evidence)

    def rule_for(self, dimension: str):
        return self._rules.get(dimension)

    # -- rules -----------------------------------------------------------

    @staticmethod
    def _score_tests(
        evidence: list[Evidence],
    ) -> tuple[int | None, NotEvaluatedReason | None]:
        ev = [e for e in evidence if e.type in {"unit_test", "test_report"}]
        if not ev:
            return None, NotEvaluatedReason.no_evidence
        if any(e.status == "missing" for e in ev):
            return None, NotEvaluatedReason.tool_unavailable
        failures = sum(1 for e in ev if e.status == "fail")
        passes = sum(1 for e in ev if e.status == "pass")
        if failures:
            return 1, None
        if passes:
            return (4 if len(ev) == passes else 3), None
        return None, NotEvaluatedReason.no_evidence

    @staticmethod
    def _score_static(
        evidence: list[Evidence],
    ) -> tuple[int | None, NotEvaluatedReason | None]:
        if not evidence:
            return None, NotEvaluatedReason.no_evidence
        if any(e.status == "missing" for e in evidence):
            return None, NotEvaluatedReason.tool_unavailable
        findings = [e for e in evidence if e.severity in SEVERITIES]
        if not findings:
            # The tool ran and reported no findings at all.
            if any(e.status == "pass" for e in evidence):
                return 4, None
            return None, NotEvaluatedReason.no_evidence
        errors = sum(1 for e in findings if e.severity == "error")
        warnings = sum(1 for e in findings if e.severity == "warning")
        if errors:
            return 1, None
        if warnings:
            return 2 if warnings > 3 else 3, None
        return 3, None

    def _score_static_quality(
        self, evidence: list[Evidence]
    ) -> tuple[int | None, NotEvaluatedReason | None]:
        return self._score_static([e for e in evidence if e.source == "detekt"])

    def _score_static_practices(
        self, evidence: list[Evidence]
    ) -> tuple[int | None, NotEvaluatedReason | None]:
        return self._score_static([e for e in evidence if e.source == "lint"])

    @staticmethod
    def _score_architecture(
        evidence: list[Evidence],
    ) -> tuple[int | None, NotEvaluatedReason | None]:
        ev = [e for e in evidence if e.type == "structure"]
        if not ev:
            return None, NotEvaluatedReason.no_evidence
        missing = sum(1 for e in ev if e.status == "missing")
        passes = sum(1 for e in ev if e.status == "pass")
        if missing and passes:
            return 2, None
        if missing:
            return 1, None
        return (4 if passes >= 2 else 3), None


def score_requirement(criterion: EvaluationCriterion) -> int | None:
    """Deterministic 0-4 score for one exercise requirement (RQ-EVA-006)."""
    evidence = criterion.evidence
    if not evidence:
        return None
    if any(e.status == "fail" and e.type != "compilation" for e in evidence):
        return 0
    if any(e.type == "unit_test" and e.status == "pass" for e in evidence):
        return 4
    if any(e.status == "pass" and e.type == "structure" for e in evidence):
        return 3
    if any(e.status == "pass" and e.type == "compilation" for e in evidence):
        return 2
    return None


def requirement_not_evaluated_reason(
    criterion: EvaluationCriterion,
) -> NotEvaluatedReason | None:
    if criterion.score is not None:
        return None
    if not criterion.evidence:
        return NotEvaluatedReason.no_evidence
    if any(e.status == "missing" for e in criterion.evidence):
        return NotEvaluatedReason.tool_unavailable
    return NotEvaluatedReason.no_evidence


class RubricEngine:
    """Deterministic scoring mechanics for any ``RubricDefinition``.

    Stateless and reusable: the engine never holds a rubric, only validates the
    definition it is handed, so two workflows cannot leak weights into each other
    (RQ-EVA-032, RQ-EVA-036).
    """

    def __init__(self, definition: RubricDefinition) -> None:
        definition.validate_weights()
        self.definition = definition
        self.scorer = DimensionScorer(definition)

    @property
    def ref(self) -> str:
        return self.definition.ref

    def weights(self) -> dict[str, float]:
        return self.definition.weights()

    def score_dimensions(self, evidence: list[Evidence]) -> dict[str, DimensionScore]:
        """Score every declared dimension from raw evidence."""
        scores: dict[str, DimensionScore] = {}
        for dimension in self.definition.dimensions:
            if dimension.id == self.definition.functional_dimension:
                continue
            value, reason = self.scorer.score(dimension.id, evidence)
            scores[dimension.id] = DimensionScore(
                dimension=dimension.id,
                weight=dimension.weight,
                score=None if value is None else float(value),
                not_evaluated_reason=reason,
            )
        return scores

    def functional_dimension_score(
        self, criteria: list[EvaluationCriterion]
    ) -> tuple[float | None, NotEvaluatedReason | None, float | None]:
        """Weighted subcriterion score inside the fixed functional dimension.

        Returns ``(score, not_evaluated_reason, subweight_sum)``. Subweights are
        renormalized over the evaluated subset so an unevaluated requirement is
        excluded from the denominator rather than counted as a failure
        (RQ-EVA-024).
        """
        scored = [c for c in criteria if c.score is not None]
        if not scored:
            return None, NotEvaluatedReason.no_evidence, None
        subweight_sum = sum(c.weight for c in scored)
        if subweight_sum <= 0:
            return None, NotEvaluatedReason.no_evidence, None
        value = sum(c.weight * float(c.score) for c in scored) / subweight_sum
        return value, None, subweight_sum

    def score(
        self,
        dimension_scores: dict[str, float | int | None],
        criteria: list[EvaluationCriterion] | None = None,
        *,
        build_failed: bool = False,
        extra_limitations: list[str] | None = None,
    ) -> ScoreBreakdown:
        """Compute the deterministic 0-100 score from supplied criterion and
        dimension scores plus evidence status (RQ-EVA-032).

        ``100 * Σ(weight × score / 4) / Σ(weight for evaluated dimensions)``
        (spec.md §Scoring). An LLM-supplied score never enters here.
        """
        criteria = list(criteria or [])
        definition = self.definition
        # Validate the subweights the caller supplied *in full*, not just the
        # scored subset: a partially evaluated functional dimension is legitimate
        # and must renormalize over its evaluated subset below (RQ-EVA-014,
        # RQ-EVA-024). Summing only scored criteria would reject that case and
        # make the renormalization unreachable.
        if any(c.score is not None for c in criteria):
            definition.validate_subweights(
                {definition.functional_dimension: sum(c.weight for c in criteria)}
            )

        resolved: dict[str, DimensionScore] = {}
        functional_subweight_sum: float | None = None
        for dimension in definition.dimensions:
            if dimension.id == definition.functional_dimension:
                value, reason, sub_sum = self.functional_dimension_score(criteria)
                if sub_sum is not None:
                    functional_subweight_sum = sub_sum
                if build_failed and dimension.id in (
                    definition.evidence_policy.build_dependent
                ):
                    value, reason = None, NotEvaluatedReason.build_failed
                resolved[dimension.id] = DimensionScore(
                    dimension=dimension.id,
                    weight=dimension.weight,
                    score=value,
                    not_evaluated_reason=reason,
                )
                continue
            supplied = dimension_scores.get(dimension.id)
            if supplied is not None:
                resolved[dimension.id] = DimensionScore(
                    dimension=dimension.id,
                    weight=dimension.weight,
                    score=float(supplied),
                )
                continue
            resolved[dimension.id] = DimensionScore(
                dimension=dimension.id,
                weight=dimension.weight,
                score=None,
                not_evaluated_reason=NotEvaluatedReason.no_evidence,
            )

        evaluated = [d for d in resolved.values() if d.score is not None]
        not_evaluated = [d for d in resolved.values() if d.score is None]
        denominator = sum(d.weight for d in evaluated) if evaluated else 0.0
        weighted_sum = sum(d.weight * (d.score or 0.0) / MAX_SCORE for d in evaluated)

        overall: float | None = None
        limitations: list[str] = list(extra_limitations or [])
        if not evaluated:
            limitations.append(
                "no rubric dimension had sufficient evidence; no score computed"
            )
        elif denominator <= 0:
            limitations.append(
                "evaluated dimensions carry zero total weight; no score computed"
            )
        elif definition.evidence_policy.renormalize:
            overall = round(100.0 * weighted_sum / denominator, 1)
        else:
            overall = round(100.0 * weighted_sum, 1)

        for dimension in not_evaluated:
            label = definition.evidence_policy.not_evaluated_label
            reason = dimension.not_evaluated_reason or NotEvaluatedReason.no_evidence
            limitations.append(f"{dimension.dimension}: {label} ({reason.value})")

        return ScoreBreakdown(
            rubric_id=definition.id,
            rubric_version=definition.version,
            overall_score=overall,
            dimension_scores={k: v.score for k, v in resolved.items()},
            evaluated_dimensions=[d.dimension for d in evaluated],
            not_evaluated_dimensions=[d.dimension for d in not_evaluated],
            dimension_reasons={
                d.dimension: (
                    d.not_evaluated_reason or NotEvaluatedReason.no_evidence
                ).value
                for d in not_evaluated
            },
            weighted_sum=weighted_sum,
            weight_denominator=denominator,
            functional_subweight_sum=functional_subweight_sum,
            limitations=limitations,
            criteria=criteria,
        )


#: The default ``/evaluate`` engine. Frozen by convention: a workflow that needs
#: other weights builds its own ``RubricDefinition`` (RQ-EVA-031).
def evaluate_engine() -> RubricEngine:
    return RubricEngine(EVALUATE_RUBRIC)


__all__ = [
    "CriterionScore",
    "DimensionScorer",
    "DimensionScore",
    "EVALUATE_RUBRIC",
    "EvidencePolicy",
    "MAX_SCORE",
    "MIN_SCORE",
    "RubricDefinition",
    "RubricDimension",
    "RubricEngine",
    "RubricSubcriterion",
    "SEVERITIES",
    "ScoreBreakdown",
    "evaluate_engine",
    "requirement_not_evaluated_reason",
    "score_requirement",
]
