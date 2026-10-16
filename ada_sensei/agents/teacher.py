"""TeacherAgent — principal orchestrator (spec 009-agent-orchestration)."""

from __future__ import annotations

import contextlib
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ..learning.stores import (
    LearningProfileStore,
)
from ..locale.service import LocaleService
from ..urns import URN
from .contracts import (
    AgentContext,
    AgentInvocationRecord,
    AgentRole,
    AgentStatus,
    SpecialistResult,
    TeacherDecision,
)
from .evaluator import EvaluatorAgent
from .planner import PlannerAgent
from .stores import AgentInvocationStore
from .trainer import TrainerAgent

if TYPE_CHECKING:
    from ..actions.base import ActionServices
    from ..cli.commands import Command
    from ..context import SessionContext


_COMMAND_INTENT_MAP: dict[str, str] = {
    "AskCommand": "ask",
    "PracticeCommand": "practice",
    "ExamplesCommand": "examples",
    "EvaluateCommand": "evaluate",
    "ExamineStartCommand": "exam_init",
    "ExamineFinishCommand": "exam_finish",
    "LearnCommand": "learn",
    "DiagnoseCommand": "diagnose",
    "LanguageCommand": "settings",
}


class TeacherAgent:
    """
    Single entry point for all student-facing actions.

    Orchestration cycle per action:
    1. Resolve locale and current stage from LearningProfile.
    2. Build a bounded AgentContext.
    3. Execute the existing action service (once) for the command.
    4. Invoke PlannerAgent, EvaluatorAgent, TrainerAgent exactly once each.
    5. Validate specialist outputs.
    6. Persist AgentInvocationRecord.
    7. Return TeacherDecision with final_response.

    Invariants:
    - Action services execute ONCE.
    - Specialists never cause duplicate Gradle/exam side effects.
    - A failed specialist is marked FAILED; the orchestrator continues if safe.
    - Specialists never modify shared state directly; persistence is done here.
    """

    def __init__(
        self,
        services: ActionServices,
        planner: PlannerAgent,
        evaluator: EvaluatorAgent,
        trainer: TrainerAgent,
        locale_service: LocaleService,
        invocation_store: AgentInvocationStore,
        profile_store: LearningProfileStore,
    ) -> None:
        self._services = services
        self._planner = planner
        self._evaluator = evaluator
        self._trainer = trainer
        self._locale_service = locale_service
        self._invocation_store = invocation_store
        self._profiles = profile_store

    # -- public entry point -----------------------------------------------

    def handle(self, command: Command, session_ctx: SessionContext) -> TeacherDecision:
        """Full orchestration cycle for one student-facing command."""
        t0 = time.monotonic()
        invocation_id = URN.make("teacher_inv")

        # 1. Resolve locale
        student_id = session_ctx.student_id or ""
        locale = self._locale_service.get_or_prompt_locale(student_id) or "en-US"

        # 2. Load learning profile for stage context
        profile = self._profiles.get(student_id)
        current_stage_id = profile.current_stage_id if profile else None

        # 3. Determine intent
        intent = _COMMAND_INTENT_MAP.get(type(command).__name__, "unknown")

        # 4. Build AgentContext
        agent_ctx = AgentContext(
            student_id=student_id,
            project_id=session_ctx.project_id,
            intent=intent,
            current_stage_id=current_stage_id,
            locale=locale,
            action_input=command,
        )

        # 5. Execute the action service (once)
        action_result, action_error = self._execute_action(command, session_ctx)

        # 6. Invoke specialists (never re-run the action)
        specialist_results: list[SpecialistResult] = []
        for specialist, role in [
            (self._planner, AgentRole.PLANNER),
            (self._evaluator, AgentRole.EVALUATOR),
            (self._trainer, AgentRole.TRAINER),
        ]:
            try:
                result = specialist.run(agent_ctx, action_result)
                specialist_results.append(result)
            except Exception as exc:  # noqa: BLE001
                # A crashed specialist never propagates — mark FAILED and continue
                from .contracts import (
                    EvaluatorPayload,
                    PlannerPayload,
                    TrainerPayload,
                )

                fallback_payload: Any
                if role == AgentRole.PLANNER:
                    fallback_payload = PlannerPayload(
                        current_stage_id=current_stage_id,
                        recommended_next_activity=None,
                        mastery_gaps=[],
                        progression_decision_ref=None,
                        learning_event_id=None,
                    )
                elif role == AgentRole.EVALUATOR:
                    fallback_payload = EvaluatorPayload(
                        diagnostic_signal=None,
                        assessment_result_ref=None,
                        criterion_gaps=[],
                        limitations=[str(exc)],
                    )
                else:
                    fallback_payload = TrainerPayload(
                        explanation="Trainer unavailable.",
                        practice_task=None,
                        hints=[],
                        recommended_resources=[],
                    )
                specialist_results.append(
                    SpecialistResult(
                        agent_id=role,
                        invocation_id=URN.make(f"{role.value}_inv"),
                        status=AgentStatus.FAILED,
                        summary=f"{role.value} crashed: {type(exc).__name__}",
                        structured_payload=fallback_payload,
                        uncertainties=[str(exc)],
                    )
                )

        # 7. Compose final response
        limitations = [
            r.summary for r in specialist_results if r.status == AgentStatus.FAILED
        ]
        if action_error:
            limitations.insert(0, f"Action error: {action_error}")

        final_response = self._compose_response(
            action_result, specialist_results, locale
        )

        # 8. Persist invocation record
        duration_ms = int((time.monotonic() - t0) * 1000)
        record = AgentInvocationRecord(
            id=invocation_id,
            student_id=student_id,
            intent=intent,
            action=type(command).__name__,
            specialist_results=[
                {
                    "agent_id": r.agent_id.value,
                    "status": r.status.value,
                    "summary": r.summary,
                    "invocation_id": r.invocation_id,
                }
                for r in specialist_results
            ],
            action_result_type=type(action_result).__name__
            if action_result
            else "None",
            locale=locale,
            model=getattr(self._services.config, "model_name", "") or "",
            status="ok" if not limitations else "partial",
            created_at=datetime.now(tz=UTC),
            duration_ms=duration_ms,
            limitations=limitations,
        )
        with contextlib.suppress(Exception):
            self._invocation_store.append(record)

        # Collect progression decision ref from planner
        progression_ref: str | None = None
        for r in specialist_results:
            if r.agent_id == AgentRole.PLANNER:
                pl = r.structured_payload
                if hasattr(pl, "progression_decision_ref"):
                    progression_ref = pl.progression_decision_ref
                break

        return TeacherDecision(
            action_result=action_result,
            specialist_results=specialist_results,
            progression_decision_ref=progression_ref,
            final_response=final_response,
            limitations=limitations,
            locale=locale,
            invocation_id=invocation_id,
        )

    # -- helpers ----------------------------------------------------------

    def _execute_action(
        self, command: Command, session_ctx: SessionContext
    ) -> tuple[Any, str | None]:
        """Run the existing action service for the command. Returns (result, error_str)."""
        from ..cli.router import CommandRouter

        try:
            router = CommandRouter(self._services)
            result = router.dispatch(command)
            return result, None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _compose_response(
        action_result: Any,
        specialist_results: list[SpecialistResult],
        locale: str,
    ) -> str:
        """Compose the final student-facing response from action + specialist outputs."""
        parts: list[str] = []

        # Lead with the action result
        if action_result is not None and hasattr(action_result, "present"):
            try:
                parts.append(action_result.present())
            except Exception:  # noqa: BLE001
                pass

        # Trainer explanation (if any and not a duplicate of action result)
        for r in specialist_results:
            if r.agent_id == AgentRole.TRAINER and r.status == AgentStatus.OK:
                pl = r.structured_payload
                if hasattr(pl, "explanation") and pl.explanation:
                    if pl.explanation not in " ".join(parts):
                        parts.append(pl.explanation)
                break

        # Planner recommendation (show gaps/next activity if something useful)
        for r in specialist_results:
            if r.agent_id == AgentRole.PLANNER and r.status == AgentStatus.OK:
                pl = r.structured_payload
                if (
                    hasattr(pl, "recommended_next_activity")
                    and pl.recommended_next_activity
                ):
                    parts.append(f"→ {pl.recommended_next_activity}")
                break

        # Failed specialists disclosure
        failed = [r for r in specialist_results if r.status == AgentStatus.FAILED]
        if failed:
            names = ", ".join(r.agent_id.value for r in failed)
            parts.append(f"[Note: {names} unavailable; response may be incomplete.]")

        return "\n\n".join(p.strip() for p in parts if p.strip()) or "(no response)"


__all__ = ["TeacherAgent"]
