"""EvaluatorAgent — diagnostic signals and assessment interpretation (spec 009).

For ask/practice/examples the agent emits a brief diagnostic signal using a
bounded LLM call (max 3 attempts). For evaluate/exam_finish it interprets the
action result without fabricating evidence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from ..urns import URN
from .contracts import (
    AgentContext,
    AgentRole,
    AgentStatus,
    EvaluatorPayload,
    SpecialistResult,
)

if TYPE_CHECKING:
    from ..llm.base import LLMClient

_DIAGNOSTIC_INTENTS = frozenset({"ask", "practice", "examples", "learn"})
_ASSESSMENT_INTENTS = frozenset({"evaluate", "exam_finish", "diagnose"})


class _DiagnosticSignal(BaseModel):
    signal: str | None  # null if nothing notable
    gaps: list[str]
    limitations: list[str]


class EvaluatorAgent:
    """
    Returns evidence-grounded evaluation annotations.
    - Never fabricates evidence or criterion scores.
    - For diagnostic intents: bounded LLM call for misconception detection.
    - For assessment intents: interprets action result without re-running tools.
    """

    def __init__(self, client: LLMClient | None, model: str = "") -> None:
        self._client = client
        self._model = model

    def run(
        self,
        ctx: AgentContext,
        action_result: object | None = None,
    ) -> SpecialistResult:
        invocation_id = URN.make("eval_inv")
        try:
            payload = self._run_inner(ctx, action_result)
            return SpecialistResult(
                agent_id=AgentRole.EVALUATOR,
                invocation_id=invocation_id,
                status=AgentStatus.OK,
                summary=(payload.diagnostic_signal or "No diagnostic signal detected."),
                structured_payload=payload,
                uncertainties=payload.limitations,
            )
        except Exception as exc:  # noqa: BLE001
            payload = EvaluatorPayload(
                diagnostic_signal=None,
                assessment_result_ref=None,
                criterion_gaps=[],
                limitations=[f"Evaluator error: {type(exc).__name__}: {exc}"],
            )
            return SpecialistResult(
                agent_id=AgentRole.EVALUATOR,
                invocation_id=invocation_id,
                status=AgentStatus.FAILED,
                summary=f"Evaluator error: {type(exc).__name__}: {exc}",
                structured_payload=payload,
            )

    def _run_inner(
        self,
        ctx: AgentContext,
        action_result: object | None,
    ) -> EvaluatorPayload:
        if ctx.intent in _ASSESSMENT_INTENTS:
            return self._interpret_assessment(ctx, action_result)
        if ctx.intent in _DIAGNOSTIC_INTENTS and self._client is not None:
            return self._diagnostic_signal(ctx, action_result)
        # not_applicable for other intents
        return EvaluatorPayload(
            diagnostic_signal=None,
            assessment_result_ref=None,
            criterion_gaps=[],
            limitations=[],
        )

    def _interpret_assessment(
        self,
        ctx: AgentContext,
        action_result: object | None,
    ) -> EvaluatorPayload:
        """Extract gaps and limitations from a completed evaluation/exam result."""
        if action_result is None:
            return EvaluatorPayload(
                diagnostic_signal=None,
                assessment_result_ref=None,
                criterion_gaps=[],
                limitations=["No assessment result available."],
            )
        # Extract limitations and gaps from the action result generically
        limitations: list[str] = []
        gaps: list[str] = []
        result_id: str | None = None

        if hasattr(action_result, "limitations"):
            limitations = list(action_result.limitations)[:5]
        if hasattr(action_result, "result"):
            inner = action_result.result
            if hasattr(inner, "limitations"):
                limitations = list(inner.limitations)[:5]
            if hasattr(inner, "exam_attempt_id"):
                result_id = inner.exam_attempt_id

        return EvaluatorPayload(
            diagnostic_signal=(
                f"Assessment completed. Limitations: {limitations[0]}"
                if limitations
                else None
            ),
            assessment_result_ref=result_id,
            criterion_gaps=gaps,
            limitations=limitations,
        )

    def _diagnostic_signal(
        self,
        ctx: AgentContext,
        action_result: object | None,
    ) -> EvaluatorPayload:
        """Minimal bounded LLM call to detect misconceptions in the student's question/response."""
        from ..llm.pipeline import StructuredPipeline

        stage_info = ctx.current_stage_id or "unknown stage"
        summary = ctx.recent_summary or ""

        messages = [
            {
                "role": "user",
                "content": (
                    f"Stage: {stage_info}. "
                    f"Student interaction summary: {summary[:400] or 'N/A'}. "
                    "Identify at most ONE specific misconception or gap that should be "
                    "recorded for future practice. If none, set signal to null. "
                    "Return gaps as a list (empty if none). Keep limitations to known unknowns."
                ),
            }
        ]
        try:
            result = StructuredPipeline.run_structured(
                self._client,
                messages,
                _DiagnosticSignal,
                model=self._model or None,
                max_attempts=3,
            )
            return EvaluatorPayload(
                diagnostic_signal=result.signal,
                assessment_result_ref=None,
                criterion_gaps=result.gaps,
                limitations=result.limitations,
            )
        except Exception as exc:  # noqa: BLE001
            return EvaluatorPayload(
                diagnostic_signal=None,
                assessment_result_ref=None,
                criterion_gaps=[],
                limitations=[f"Diagnostic unavailable: {type(exc).__name__}"],
            )


__all__ = ["EvaluatorAgent"]
