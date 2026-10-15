"""``/evaluate`` — the workflow adapter over the reusable evaluation engine.

This module owns the ``/evaluate`` workflow only: exercise resolution, the
Gradle confirmation policy, the default rubric, and persistence. Evidence
collection, requirement matching, rubric mechanics, and structured
interpretation live in ``ada_sensei.evaluation`` (ADR-022), which has no CLI/TUI
dependency and is reusable by other workflows.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..evaluation import (
    EVALUATE_RUBRIC,
    AndroidProjectAnalyzer,
    EvaluationContext,
    EvaluationEngine,
    EvaluationExecutionPolicy,
    EvidenceContext,
    GradleTool,
    ProjectContext,
    RequirementMatcher,
    RubricEngine,
    StaticAnalysisTool,
    TestTool,
    evaluate_engine,
    unsupported_claim_summary,
)
from ..models import EvaluationResult, Exercise
from ..tools.subprocess import SubprocessRunner
from .base import ActionResult, ActionServices


class EvaluationAborted(Exception):
    pass


class InstrumentedNotSupportedError(Exception):
    pass


@dataclass
class EvaluateInput:
    exercise_id: str | None = None
    instrumented: bool = False
    confirmed: bool = False


@dataclass
class EvalResult(ActionResult):
    result: EvaluationResult

    def present(self) -> str:
        overall = (
            f"{self.result.overall_score}"
            if self.result.overall_score is not None
            else "not evaluated"
        )
        rubric = self.result.rubric_id
        version = self.result.rubric_version
        parts = [f"Overall score: {overall}"]
        if rubric and version:
            parts.append(f"Rubric: {rubric}:{version}")
        for criterion in self.result.criteria:
            label = criterion.requirement_id or criterion.dimension
            score = (
                criterion.score
                if criterion.score is not None
                else "not evaluated"
            )
            parts.append(f"- {label}: {score}")
        if self.result.strengths:
            parts.append(
                "Strengths:\n" + "\n".join(f"- {s}" for s in self.result.strengths)
            )
        if self.result.weaknesses:
            parts.append(
                "Weaknesses:\n"
                + "\n".join(f"- {w}" for w in self.result.weaknesses)
            )
        if self.result.feedback:
            parts.append(self.result.feedback)
        if self.result.recommendations:
            parts.append(
                "Recommendations:\n"
                + "\n".join(f"- {r}" for r in self.result.recommendations)
            )
        if self.result.next_learning_activity:
            parts.append(
                f"Next learning activity: {self.result.next_learning_activity}"
            )
        if self.result.unsupported_claims:
            parts.append(unsupported_claim_summary(self.result.unsupported_claims))
        if self.result.limitations:
            parts.append(
                "Limitations:\n"
                + "\n".join(f"- {lim}" for lim in self.result.limitations)
            )
        return "\n\n".join(parts)


class EvaluateAction:
    """Orchestrates the shared engine with the default ``evaluate-default:v1``."""

    def __init__(
        self,
        services: ActionServices,
        runner: SubprocessRunner | None = None,
        engine: EvaluationEngine | None = None,
    ) -> None:
        self.services = services
        self._runner = runner
        self.engine = engine or EvaluationEngine()
        self.rubric = EVALUATE_RUBRIC

    def run(self, inp: EvaluateInput | None = None) -> EvalResult:
        inp = inp or EvaluateInput()
        if inp.instrumented:
            raise InstrumentedNotSupportedError(
                "--instrumented (connectedAndroidTest) is reserved for a future "
                "option and is not supported now"
            )

        project = self._resolve_project()
        exercise = self._resolve_exercise(inp.exercise_id)
        policy = self._resolve_policy(inp)

        blocked = policy.blocked_reason()
        if blocked is not None:
            raise EvaluationAborted(blocked)

        evidence = self.engine.collect_evidence(
            project, exercise, policy, runner=self._runner
        )
        result = self.engine.evaluate(
            evidence,
            self.rubric,
            self._evaluation_context(exercise),
            exercise=exercise,
            client=self.services.client,
        )
        self._persist(result)
        return EvalResult(result=result)

    # -- resolution -------------------------------------------------------

    def _resolve_project(self) -> ProjectContext:
        project_path = self.services.config.project.path
        if project_path in (None, "", "."):
            raise LookupError("no active project configured")
        return ProjectContext.from_path(str(project_path))

    def _resolve_exercise(self, exercise_id: str | None) -> Exercise | None:
        """RQ-EVA-017: explicit option, then session context, then structural."""
        uri = exercise_id or self.services.context.current_exercise_id
        if not uri:
            return None
        exercise = self.services.exercises.get(uri)
        if exercise is None:
            raise LookupError(f"unknown exercise: {uri}")
        return exercise

    def _resolve_policy(self, inp: EvaluateInput) -> EvaluationExecutionPolicy:
        """RQ-EVA-019/020/021/023: the single confirmation and scope gate."""
        return EvaluationExecutionPolicy(
            gradle_confirmed=inp.confirmed,
            run_build=True,
            run_unit_tests=True,
            run_lint=True,
            run_detekt=True,
            run_instrumented=False,
            timeout_seconds=self.services.config.tools.timeout_seconds,
        )

    def _evaluation_context(
        self, exercise: Exercise | None
    ) -> EvaluationContext:
        return EvaluationContext(
            student_id=self.services.context.student_id,
            attempt_id=self.services.context.attempt_id or None,
            exercise_id=exercise.id if exercise else None,
            llm_model=self.services.config.llm.model,
            llm_temperature=self.services.config.llm.temperature,
            max_attempts=self.services.config.llm.max_attempts,
        )

    # -- persistence ------------------------------------------------------

    def _persist(self, result: EvaluationResult) -> None:
        """RQ-EVA-016/025/026/027: failures are reported, never swallowed."""
        student_id = result.student_id
        attempt_id = result.attempt_id
        try:
            self.services.results.save(result)
        except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
            result.limitations.append(
                f"result {result.id} was NOT persisted: {exc}"
            )
        if attempt_id:
            try:
                self.services.attempts.mark_completed(attempt_id)
            except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
                result.limitations.append(
                    f"attempt {attempt_id} was NOT marked completed: {exc}"
                )
        if student_id:
            try:
                self.services.history.append_evaluation(student_id, result)
            except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
                result.limitations.append(
                    f"evaluation outcome NOT appended to history for "
                    f"{student_id}: {exc}"
                )


__all__ = [
    "AndroidProjectAnalyzer",
    "EvalResult",
    "EvaluateAction",
    "EvaluateInput",
    "EvaluationAborted",
    "EvaluationContext",
    "EvaluationEngine",
    "EvaluationExecutionPolicy",
    "EvidenceContext",
    "GradleTool",
    "InstrumentedNotSupportedError",
    "ProjectContext",
    "RequirementMatcher",
    "RubricEngine",
    "StaticAnalysisTool",
    "TestTool",
    "evaluate_engine",
]
