"""The reusable evaluation engine (ADR-022, RQ-EVA-028/029/032/033/036).

``EvaluationEngine`` coordinates project analysis, deterministic evidence
collection, requirement matching, rubric mechanics, and structured
interpretation. It knows nothing about ``/evaluate``, the CLI, or the TUI: a
caller drives it with a project, an optional exercise, an execution policy, and
a rubric definition. ``EvaluateAction`` is one such caller; ``007-examine`` is
another.
"""

from __future__ import annotations

from pathlib import Path

from ..models import (
    EvaluationCriterion,
    EvaluationResult,
    Evidence,
    Exercise,
    NotEvaluatedReason,
    UnsupportedClaim,
)
from ..urns import URN
from .agent import (
    EvaluationAgent,
    GroundedInterpretation,
    unavailable_interpretation,
)
from .evidence import EvidenceCollector
from .matcher import RequirementMatch, RequirementMatcher
from .models import (
    EvaluationContext,
    EvaluationExecutionPolicy,
    EvidenceContext,
    ProjectContext,
    ScoreBreakdown,
)
from .rubric import RubricDefinition, RubricEngine

NO_EXERCISE_LIMITATION = (
    "no exercise resolved; structural evaluation only, functional "
    "requirements are not evaluated"
)


class EvaluationEngine:
    """Reusable evidence-and-scoring boundary, free of CLI/TUI concerns."""

    def __init__(
        self,
        *,
        analyzer_collector: type[EvidenceCollector] = EvidenceCollector,
        matcher_factory: type[RequirementMatcher] = RequirementMatcher,
        agent_factory: type[EvaluationAgent] = EvaluationAgent,
    ) -> None:
        self._collector_type = analyzer_collector
        self._matcher_type = matcher_factory
        self._agent_type = agent_factory

    # -- stage 1: evidence ------------------------------------------------

    def collect_evidence(
        self,
        project: ProjectContext | str | Path,
        exercise: Exercise | None = None,
        execution_policy: EvaluationExecutionPolicy | None = None,
        *,
        runner=None,
    ) -> EvidenceContext:
        """Run the default evidence scope and return a neutral context.

        The same context is reusable by any workflow; nothing here depends on
        which workflow asked for it (RQ-EVA-029).
        """
        ctx = (
            project
            if isinstance(project, ProjectContext)
            else ProjectContext.from_path(project)
        )
        policy = execution_policy or EvaluationExecutionPolicy()
        collector = self._collector_type(ctx, policy, runner=runner)
        return collector.collect()

    # -- stage 2: scoring --------------------------------------------------

    def build_matcher(self, exercise: Exercise | None) -> RequirementMatcher:
        """Requirement matching, callable independently of any action
        (RQ-EVA-033)."""
        return self._matcher_type(exercise)

    def match_requirements(
        self, exercise: Exercise | None, evidence: EvidenceContext
    ) -> RequirementMatch:
        build_failed = self.build_failed(evidence)
        return self.build_matcher(exercise).match(evidence, build_failed=build_failed)

    def build_agent(
        self, context: EvaluationContext, client: object | None
    ) -> EvaluationAgent:
        return self._agent_type(
            client,
            model=context.llm_model,
            temperature=context.llm_temperature,
            max_attempts=context.max_attempts,
        )

    def evaluate(
        self,
        evidence: EvidenceContext,
        rubric: RubricDefinition,
        context: EvaluationContext,
        *,
        exercise: Exercise | None = None,
        client: object | None = None,
    ) -> EvaluationResult:
        """Score evidence against ``rubric`` and interpret the result.

        The overall score is recomputed deterministically here; the LLM's
        interpretation is qualitative only (RQ-EVA-007, RQ-EVA-032).
        """
        engine = RubricEngine(rubric)
        limitations: list[str] = list(evidence.limitations)
        build_failed = self.build_failed(evidence)

        if exercise is None:
            limitations.append(NO_EXERCISE_LIMITATION)

        match = (
            self.match_requirements(exercise, evidence)
            if exercise is not None
            else RequirementMatch(unmatched_evidence=list(evidence.evidence))
        )
        criteria = list(match.criteria)

        dimension_scores = engine.score_dimensions(evidence.evidence)
        supplied = {d: s.score for d, s in dimension_scores.items()}

        breakdown: ScoreBreakdown = engine.score(
            supplied,
            criteria,
            build_failed=build_failed,
            extra_limitations=limitations,
        )
        limitations = list(breakdown.limitations)

        criteria = self._annotate_criteria(criteria, breakdown)
        interpretation, interpretation_limitations = self._interpret(
            evidence, breakdown.dimension_scores, context, client
        )
        limitations.extend(interpretation_limitations)

        result = EvaluationResult(
            id=URN.make("result"),
            attempt_id=context.attempt_id,
            exercise_id=exercise.id if exercise else None,
            student_id=context.student_id,
            project_id=evidence.project_id,
            rubric_id=rubric.id,
            rubric_version=rubric.version,
            overall_score=breakdown.overall_score,
            criteria=[
                *criteria,
                *self._functional_placeholder(rubric, breakdown, criteria),
                *self._top_level_criteria(rubric, breakdown),
            ],
            dimension_scores=breakdown.dimension_scores,
            evidence=list(evidence.evidence),
            strengths=interpretation.strengths(),
            weaknesses=interpretation.weaknesses(),
            feedback=interpretation.interpretation.feedback,
            recommendations=interpretation.recommendations(),
            next_learning_activity=(
                interpretation.interpretation.next_learning_activity
            ),
            limitations=limitations,
            not_evaluated=list(breakdown.not_evaluated_dimensions),
            unsupported_claims=list(interpretation.unsupported_claims),
        )
        return result

    # -- shared helpers ----------------------------------------------------

    @staticmethod
    def build_failed(evidence: EvidenceContext) -> bool:
        """RQ-EVA-018: a failed build blocks compilation-dependent criteria."""
        return any(
            e.type == "compilation" and e.status == "fail" for e in evidence.evidence
        )

    def _interpret(
        self,
        evidence: EvidenceContext,
        dimension_scores: dict[str, float | None],
        context: EvaluationContext,
        client: object | None,
    ) -> tuple[GroundedInterpretation, list[str]]:
        agent = self.build_agent(context, client)
        try:
            interpretation = agent.interpret(evidence, dimension_scores)
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            limitation = (
                "LLM interpretation failed (structured output or provider): "
                f"{type(exc).__name__}: {exc}"
            )
            return unavailable_interpretation(limitation), [limitation]
        extra: list[str] = list(interpretation.interpretation.limitations)
        if interpretation.unsupported_claims:
            extra.append(
                f"{len(interpretation.unsupported_claims)} LLM claim(s) could not be "
                "grounded in collected evidence and were excluded"
            )
        return interpretation, extra

    @staticmethod
    def _annotate_criteria(
        criteria: list[EvaluationCriterion], breakdown: ScoreBreakdown
    ) -> list[EvaluationCriterion]:
        for criterion in criteria:
            if criterion.score is None and criterion.not_evaluated_reason is None:
                criterion.not_evaluated_reason = NotEvaluatedReason.no_evidence
        return criteria

    @staticmethod
    def _functional_placeholder(
        rubric: RubricDefinition,
        breakdown: ScoreBreakdown,
        criteria: list[EvaluationCriterion],
    ) -> list[EvaluationCriterion]:
        """With no exercise there are no requirement criteria, so the functional
        dimension would vanish from the report. Emit one explicit
        ``not_evaluated`` criterion instead of a silent omission (RQ-EVA-014).
        """
        if any(c.dimension == rubric.functional_dimension for c in criteria):
            return []
        return [
            EvaluationCriterion(
                requirement_id=None,
                dimension=rubric.functional_dimension,
                weight=1.0,
                score=None,
                not_evaluated_reason=NotEvaluatedReason.no_exercise,
            )
        ]

    @staticmethod
    def _top_level_criteria(
        rubric: RubricDefinition, breakdown: ScoreBreakdown
    ) -> list[EvaluationCriterion]:
        """One criterion per non-functional dimension, carrying its weight."""
        criteria: list[EvaluationCriterion] = []
        for dimension in rubric.dimensions:
            if dimension.id == rubric.functional_dimension:
                continue
            score = breakdown.dimension_scores.get(dimension.id)
            criteria.append(
                EvaluationCriterion(
                    requirement_id=None,
                    dimension=dimension.id,
                    weight=dimension.weight,
                    score=round(score) if score is not None else None,
                    not_evaluated_reason=(
                        None
                        if score is not None
                        else NotEvaluatedReason.no_evidence
                    ),
                )
            )
        return criteria


def unsupported_claim_summary(claims: list[UnsupportedClaim]) -> str:
    if not claims:
        return ""
    lines = [f"- [{c.kind}] {c.claim} ({c.reason})" for c in claims]
    return "Unsupported claims excluded from the result:\n" + "\n".join(lines)


def evidence_reference_table(evidence: list[Evidence]) -> str:
    """Traceable ``ev://`` -> description listing used by reports."""
    return "\n".join(
        f"{e.id} [{e.source}/{e.type}/{e.status}] {e.message[:160]}"
        for e in evidence
        if e.id
    )


__all__ = [
    "EvaluationEngine",
    "NO_EXERCISE_LIMITATION",
    "evidence_reference_table",
    "unsupported_claim_summary",
]
