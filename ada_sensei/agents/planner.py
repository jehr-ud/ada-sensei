"""PlannerAgent — deterministic progression and learning-event tracking (spec 009)."""
from __future__ import annotations

from datetime import UTC, datetime

from ..learning.catalog import LearningCatalogLoader
from ..learning.models import LearningEvent
from ..learning.progression import ProgressionPolicyEngine
from ..learning.stores import (
    LearningEventStore,
    LearningProfileStore,
    MasteryAssessmentStore,
    ProgressionDecisionStore,
)
from ..urns import URN
from .contracts import (
    AgentContext,
    AgentRole,
    AgentStatus,
    PlannerPayload,
    SpecialistResult,
)

_ASSESS_INTENTS = frozenset({"evaluate", "exam_finish", "diagnose"})


class PlannerAgent:
    """
    Deterministic progression and learning evidence tracking.
    Makes NO direct LLM calls — only applies configured policy gates.
    """

    def __init__(
        self,
        profile_store: LearningProfileStore,
        event_store: LearningEventStore,
        assessment_store: MasteryAssessmentStore,
        decision_store: ProgressionDecisionStore,
        catalog_loader: LearningCatalogLoader | None = None,
    ) -> None:
        self._profiles = profile_store
        self._events = event_store
        self._assessments = assessment_store
        self._decisions = decision_store
        self._catalog_loader = catalog_loader or LearningCatalogLoader()
        self._policy_engine = ProgressionPolicyEngine()

    def run(
        self,
        ctx: AgentContext,
        action_result: object | None = None,
    ) -> SpecialistResult:
        invocation_id = URN.make("planner_inv")
        try:
            payload = self._run_inner(ctx, action_result)
            return SpecialistResult(
                agent_id=AgentRole.PLANNER,
                invocation_id=invocation_id,
                status=AgentStatus.OK,
                summary=(
                    f"Stage: {payload.current_stage_id or 'unknown'}. "
                    f"Next: {payload.recommended_next_activity or 'continue learning'}."
                ),
                structured_payload=payload,
            )
        except Exception as exc:  # noqa: BLE001
            payload = PlannerPayload(
                current_stage_id=ctx.current_stage_id,
                recommended_next_activity=None,
                mastery_gaps=[],
                progression_decision_ref=None,
                learning_event_id=None,
            )
            return SpecialistResult(
                agent_id=AgentRole.PLANNER,
                invocation_id=invocation_id,
                status=AgentStatus.FAILED,
                summary=f"Planner error: {type(exc).__name__}: {exc}",
                structured_payload=payload,
                uncertainties=[str(exc)],
            )

    def _run_inner(
        self,
        ctx: AgentContext,
        action_result: object | None,
    ) -> PlannerPayload:
        # Record a learning event for this interaction
        event = LearningEvent(
            id=URN.make("learning"),
            student_id=ctx.student_id,
            stage_id=ctx.current_stage_id or "unknown",
            event_type=_intent_to_event_type(ctx.intent),
            action=ctx.intent,
            agent_invocation_id=None,
            created_at=datetime.now(tz=UTC),
        )
        self._events.append(event)

        # Check for the latest progression decision to surface gaps
        gaps: list[str] = []
        decision_ref: str | None = None
        if ctx.current_stage_id:
            latest_decision = self._decisions.get_latest(
                ctx.student_id, ctx.current_stage_id
            )
            if latest_decision is not None:
                decision_ref = latest_decision.decision_id
                gaps = [
                    g.reason
                    for g in latest_decision.gate_results
                    if not g.passed
                ]

        # Determine recommended next activity
        recommended = _recommended_activity(ctx.intent, ctx.current_stage_id, gaps)

        return PlannerPayload(
            current_stage_id=ctx.current_stage_id,
            recommended_next_activity=recommended,
            mastery_gaps=gaps,
            progression_decision_ref=decision_ref,
            learning_event_id=event.id,
        )


def _intent_to_event_type(intent: str) -> str:
    mapping = {
        "ask": "ask",
        "practice": "practice",
        "evaluate": "assess",
        "exam_init": "assess",
        "exam_finish": "assess",
        "learn": "study",
        "diagnose": "diagnose",
        "examples": "study",
        "onboard": "onboard",
    }
    return mapping.get(intent, "study")


def _recommended_activity(
    intent: str,
    stage_id: str | None,
    gaps: list[str],
) -> str | None:
    if not stage_id:
        return "Complete onboarding to establish your starting stage."
    if gaps:
        return (
            "Focus on the following gaps before requesting a mastery assessment: "
            + "; ".join(gaps[:3])
            + ("…" if len(gaps) > 3 else ".")
        )
    if intent in ("evaluate", "exam_finish"):
        return "Review the assessment feedback and practice any failing criteria."
    return "Continue learning the current stage concepts."


__all__ = ["PlannerAgent"]
