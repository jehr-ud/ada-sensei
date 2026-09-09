from __future__ import annotations

from dataclasses import dataclass, field

from ..llm import StructuredPipeline
from ..models import (
    AssistanceLevel,
    Attempt,
    Difficulty,
    EvaluationCriterion,
    Exercise,
    PracticeResult,
    Requirement,
)
from ..urns import URN
from .base import ActionServices


class PracticeInputError(ValueError):
    pass


@dataclass
class PracticeInput:
    topic: str | None = None
    difficulty: Difficulty | None = None
    objective: str | None = None
    adaptive: bool = True

    @classmethod
    def from_options(
        cls,
        topic: str | None = None,
        difficulty: str | None = None,
        objective: str | None = None,
        adaptive: bool = True,
    ) -> PracticeInput:
        resolved_difficulty: Difficulty | None = None
        if difficulty is not None:
            try:
                resolved_difficulty = Difficulty(difficulty)
            except ValueError:
                raise PracticeInputError(
                    f"invalid difficulty {difficulty!r}; "
                    f"choose one of beginner, intermediate, advanced"
                ) from None
        return cls(
            topic=topic,
            difficulty=resolved_difficulty,
            objective=objective,
            adaptive=adaptive,
        )


@dataclass
class StudentContext:
    history_summary: str = "(no history available)"
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


class ExerciseSpecification:
    def __init__(
        self,
        topic: str | None,
        difficulty: Difficulty | None,
        objective: str | None,
        student: StudentContext | None,
    ) -> None:
        self.topic = topic
        self.difficulty = difficulty
        self.objective = objective
        self.student = student or StudentContext()

    def render(self) -> str:
        parts = [f"Topic: {self.topic or 'compose-state'}"]
        level = self.difficulty.value if self.difficulty else "intermediate"
        parts.append(f"Difficulty: {level}")
        if self.objective:
            parts.append(f"Objective: {self.objective}")
        parts.append(f"Student context: {self.student.history_summary}")
        return "\n".join(parts)


class PracticePrompt:
    SYSTEM = (
        "You are ADA Sensei, an Android tutor. Generate ONE solvable Android "
        "programming exercise as strictly valid JSON. Do NOT provide the complete "
        "solution. The exercise must be self-contained so a student can implement it "
        "independently. Include a stable id and functional requirements each with a "
        "stable req:// id. evaluation_criteria must reference those requirement_ids "
        "and belong to the functional_requirements dimension with normalized "
        "subweights summing to 1.0. Provide progressive hints, ordered from vague to "
        "specific."
    )

    @classmethod
    def messages(cls, spec: ExerciseSpecification) -> list[dict[str, str]]:
        user = (
            "Generate a programming exercise for the following specification.\n\n"
            f"{spec.render()}\n\n"
            "Return JSON matching the Exercise schema. Set source=\"generated\". "
            "Each requirement id must be a req:// urn. Provide 1-6 hints. "
            "evaluation_criteria must contain one entry per requirement with "
            "requirement_id set, dimension=\"functional_requirements\", and weights "
            "that sum to 1.0."
        )
        return [{"role": "user", "content": user}]


class PracticeAction:
    def __init__(self, services: ActionServices) -> None:
        self.services = services

    def run(self, inp: PracticeInput | None = None) -> PracticeResult:
        inp = inp or PracticeInput()
        student_id = self.services.require_student()

        student = (
            self._defaults_from_history(student_id)
            if inp.adaptive
            else StudentContext(history_summary="(adaptive disabled)")
        )

        spec = ExerciseSpecification(
            topic=inp.topic,
            difficulty=inp.difficulty,
            objective=inp.objective,
            student=student,
        )
        messages = PracticePrompt.messages(spec)

        pipeline = StructuredPipeline(
            self.services.client,
            max_attempts=self.services.config.llm.max_attempts,
            temperature=self.services.config.llm.temperature,
        )
        exercise = pipeline.run(
            messages, Exercise, model=self.services.config.llm.model
        )
        self._ensure_requirement_ids(exercise)
        self._ensure_criteria(exercise)

        project_path = self.services.config.project.path
        project_id = (
            URN.project_id_from_path(str(project_path))
            if project_path not in (None, "")
            else None
        )

        saved = self.services.exercises.save(exercise)

        attempt = Attempt(
            id=URN.make("attempt"),
            student_id=student_id,
            project_id=project_id,
            exercise_id=exercise.id,
            assistance_level=AssistanceLevel.guiding_question,
        )
        self.services.attempts.save(attempt)

        self.services.context.set_exercise(exercise.id)
        self.services.context.attempt_id = attempt.id
        if project_path not in ("", None):
            self.services.context.set_project(project_path)

        self.services.history.record_exercise_attempted(
            student_id, exercise.id, attempt.id
        )

        return PracticeResult(
            exercise=saved,
            message=f"exercise {exercise.id} generated; attempt {attempt.id} started",
        )

    def _defaults_from_history(self, student_id: str) -> StudentContext:
        profile = self.services.history.get(student_id)
        if profile is None:
            return StudentContext()
        return StudentContext(
            history_summary=profile.summary,
            strengths=list(profile.strengths),
            weaknesses=list(profile.weaknesses),
        )

    @staticmethod
    def _ensure_requirement_ids(exercise: Exercise) -> None:
        for req in exercise.requirements:
            if not req.id.startswith("req://"):
                req.id = URN.make("req")
        if not exercise.requirements:
            req = Requirement(
                id=URN.make("req"), summary=exercise.objective or "implement"
            )
            exercise.requirements.append(req)

    @staticmethod
    def _ensure_criteria(exercise: Exercise) -> None:
        req_ids = [r.id for r in exercise.requirements]
        if exercise.evaluation_criteria:
            weight = 1.0 / len(req_ids)
            exercise.evaluation_criteria = [
                EvaluationCriterion(
                    requirement_id=c.requirement_id,
                    dimension="functional_requirements",
                    weight=weight,
                )
                for c in exercise.evaluation_criteria
                if c.requirement_id in req_ids
            ] or []
        for rid in req_ids:
            if not any(c.requirement_id == rid for c in exercise.evaluation_criteria):
                exercise.evaluation_criteria.append(
                    EvaluationCriterion(
                        requirement_id=rid,
                        dimension="functional_requirements",
                        weight=1.0 / len(req_ids),
                    )
                )
