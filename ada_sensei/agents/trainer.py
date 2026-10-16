"""TrainerAgent — teaching, practice, and stage-appropriate explanation (spec 009)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from ..urns import URN
from .contracts import (
    AgentContext,
    AgentRole,
    AgentStatus,
    SpecialistResult,
    TrainerPayload,
)

if TYPE_CHECKING:
    from ..llm.base import LLMClient

_TEACH_INTENTS = frozenset({"ask", "examples", "learn"})
_PRACTICE_INTENTS = frozenset({"practice"})
_ASSESSMENT_INTENTS = frozenset({"evaluate", "exam_finish", "diagnose"})


class _TrainerResponse(BaseModel):
    explanation: str
    practice_task: str | None = None
    hints: list[str] = []
    recommended_resources: list[str] = []


class TrainerAgent:
    """
    Provides explanations, examples, hints, and practice tasks adapted to the
    current stage and locale. Does NOT decide progression or invent evidence.
    """

    def __init__(self, client: LLMClient | None, model: str = "") -> None:
        self._client = client
        self._model = model

    def run(
        self,
        ctx: AgentContext,
        action_result: object | None = None,
    ) -> SpecialistResult:
        invocation_id = URN.make("trainer_inv")
        try:
            payload = self._run_inner(ctx, action_result)
            return SpecialistResult(
                agent_id=AgentRole.TRAINER,
                invocation_id=invocation_id,
                status=AgentStatus.OK,
                summary=payload.explanation[:120]
                + ("…" if len(payload.explanation) > 120 else ""),
                structured_payload=payload,
            )
        except Exception as exc:  # noqa: BLE001
            payload = TrainerPayload(
                explanation=f"Trainer unavailable: {type(exc).__name__}",
                practice_task=None,
                hints=[],
                recommended_resources=[],
            )
            return SpecialistResult(
                agent_id=AgentRole.TRAINER,
                invocation_id=invocation_id,
                status=AgentStatus.FAILED,
                summary=f"Trainer error: {type(exc).__name__}: {exc}",
                structured_payload=payload,
                uncertainties=[str(exc)],
            )

    def _run_inner(
        self,
        ctx: AgentContext,
        action_result: object | None,
    ) -> TrainerPayload:
        if ctx.intent in _ASSESSMENT_INTENTS:
            return self._post_assessment_feedback(ctx, action_result)
        if self._client is None:
            return TrainerPayload(
                explanation="LLM not available; no explanation generated.",
                practice_task=None,
                hints=[],
                recommended_resources=[],
            )
        return self._generate_response(ctx)

    def _generate_response(self, ctx: AgentContext) -> TrainerPayload:
        from ..llm.pipeline import StructuredPipeline

        stage_info = ctx.current_stage_id or "the current stage"
        locale_instruction = (
            "Respond in Spanish (Colombian Spanish)."
            if ctx.locale == "es-CO"
            else "Respond in English."
        )
        intent_instruction = _intent_instruction(ctx.intent)
        stage_hint = ""
        if stage_info == "android-basic-application" or "android-basic" in str(
            stage_info
        ):
            stage_hint = (
                "For the Basic Android Application stage, if this is practice/learn context, "
                "propose a small, personalized Android app idea (with app title, purpose, "
                "functional requirements, acceptance criteria, suggested screens, data model, "
                "test scenarios, mapping to learning objectives, and explicit exclusions). "
                "Do not require external APIs, auth, remote DB, or later-stage infra. "
                "Ask the student to accept or refine before starting. "
            )
        messages = [
            {
                "role": "user",
                "content": (
                    f"{locale_instruction} "
                    f"Student is working on: {stage_info}. "
                    f"{intent_instruction} "
                    f"{stage_hint}"
                    f"Context: {ctx.recent_summary[:300] or 'N/A'}. "
                    "Provide a pedagogical explanation/response. "
                    "Do NOT decide mastery or progression. "
                    "Favor guidance and hints over complete solutions unless explicitly needed."
                ),
            }
        ]
        try:
            result = StructuredPipeline.run_structured(
                self._client,
                messages,
                _TrainerResponse,
                model=self._model or None,
                max_attempts=3,
            )
            return TrainerPayload(
                explanation=result.explanation,
                practice_task=result.practice_task,
                hints=result.hints,
                recommended_resources=result.recommended_resources,
            )
        except Exception as exc:  # noqa: BLE001
            return TrainerPayload(
                explanation=f"Could not generate explanation: {type(exc).__name__}",
                practice_task=None,
                hints=[],
                recommended_resources=[],
            )

    def _post_assessment_feedback(
        self,
        ctx: AgentContext,
        action_result: object | None,
    ) -> TrainerPayload:
        """After an evaluation/exam, give targeted study recommendations."""
        if action_result is None:
            return TrainerPayload(
                explanation="Assessment complete. Review the results and plan your next practice.",
                practice_task=None,
                hints=[],
                recommended_resources=[],
            )
        # Try to extract the presentation text from the result
        presented = ""
        if hasattr(action_result, "present"):
            try:
                presented = action_result.present()[:400]
            except Exception:  # noqa: BLE001
                pass
        return TrainerPayload(
            explanation=(
                f"Assessment complete. Study the feedback and practice the gaps identified. "
                f"{presented[:200] if presented else ''}"
            ).strip(),
            practice_task=None,
            hints=["Focus on the criteria that did not meet the minimum score."],
            recommended_resources=[],
        )


def _intent_instruction(intent: str) -> str:
    if intent == "ask":
        return "Answer the student's question pedagogically."
    if intent == "practice":
        return "Generate a practice task appropriate to the stage level."
    if intent == "examples":
        return "Provide a clear, minimal, teachable example."
    if intent == "learn":
        return "Explain the key concepts of this stage clearly."
    return "Provide appropriate educational support."


__all__ = ["TrainerAgent"]
