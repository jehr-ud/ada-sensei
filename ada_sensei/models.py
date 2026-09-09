from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .urns import URN


class Timestamps:
    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)


class Difficulty(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class AssistanceLevel(StrEnum):
    guiding_question = "guiding_question"
    hint = "hint"
    conceptual_explanation = "conceptual_explanation"
    code_fragment = "code_fragment"
    solution = "solution"


class ExerciseSource(StrEnum):
    generated = "generated"
    curated = "curated"


class AttemptStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"


class ExampleSource(StrEnum):
    curated = "curated"
    generated = "generated"


ASSISTANCE_LEVELS = list(AssistanceLevel)


class Topic(BaseModel):
    name: str

    model_config = ConfigDict(frozen=True)


class Requirement(BaseModel):
    id: str = Field(default_factory=lambda: URN.make("req"))
    summary: str = ""


class Evidence(BaseModel):
    source: str = "file"
    type: str = "structure"
    severity: str | None = None
    status: str = "pass"
    message: str = ""
    file: str | None = None
    line: int | None = None
    command: str | None = None


class EvaluationCriterion(BaseModel):
    requirement_id: str | None = None
    dimension: str = "functional_requirements"
    weight: float = 1.0
    score: int | None = None
    evidence: list[Evidence] = Field(default_factory=list)


Criterion = EvaluationCriterion


class Exercise(BaseModel):
    id: str = Field(default_factory=lambda: URN.make("exercise"))
    title: str = ""
    topic: str = ""
    difficulty: Difficulty = Difficulty.intermediate
    objective: str = ""
    statement: str = ""
    requirements: list[Requirement] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    evaluation_criteria: list[EvaluationCriterion] = Field(default_factory=list)
    source: ExerciseSource = ExerciseSource.generated
    created_at: datetime = Field(default_factory=Timestamps.now)


class Attempt(BaseModel):
    id: str = Field(default_factory=lambda: URN.make("attempt"))
    student_id: str | None = None
    project_id: str | None = None
    exercise_id: str | None = None
    assistance_level: AssistanceLevel = AssistanceLevel.guiding_question
    hints_used: list[str] = Field(default_factory=list)
    conversation_ref: str | None = None
    started_at: datetime = Field(default_factory=Timestamps.now)
    status: AttemptStatus = AttemptStatus.in_progress


class LearningEvent(BaseModel):
    id: str = Field(default_factory=lambda: URN.make("learning"))
    type: str = "event"
    student_id: str | None = None
    project_id: str | None = None
    exercise_id: str | None = None
    attempt_id: str | None = None
    result_id: str | None = None
    payload: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=Timestamps.now)


class StudentProfile(BaseModel):
    id: str | None = None
    student_id: str
    name: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recurring_errors: list[str] = Field(default_factory=list)
    events: list[LearningEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=Timestamps.now)

    @property
    def summary(self) -> str:
        exc_count = sum(1 for e in self.events if e.type == "exercise_attempted")
        passed = sum(
            1
            for e in self.events
            if e.type == "exercise_result" and e.payload.get("passed")
        )
        return (
            f"exercises_attempted={exc_count}, passed={passed}, "
            f"strengths={','.join(self.strengths) or 'none'}, "
            f"weaknesses={','.join(self.weaknesses) or 'none'}"
        )


class EvaluationResult(BaseModel):
    id: str = Field(default_factory=lambda: URN.make("result"))
    attempt_id: str | None = None
    exercise_id: str | None = None
    student_id: str | None = None
    project_id: str | None = None
    overall_score: float | None = None
    criteria: list[EvaluationCriterion] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    feedback: str = ""
    recommendations: list[str] = Field(default_factory=list)
    next_learning_activity: str = ""
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=Timestamps.now)


class PracticeResult(BaseModel):
    exercise: Exercise
    message: str = ""


class Answer(BaseModel):
    id: str = Field(default_factory=lambda: URN.make("answer"))
    question: str = ""
    classification: str = "conceptual"
    assistance_level: AssistanceLevel = AssistanceLevel.conceptual_explanation
    response: str = ""
    citations: list[str] = Field(default_factory=list)
    uncertainty: bool = False
    created_at: datetime = Field(default_factory=Timestamps.now)


class CommonMistake(BaseModel):
    incorrect_code: str = ""
    explanation: str = ""


class ExampleResult(BaseModel):
    id: str | None = Field(default_factory=lambda: URN.make("example"))
    concept: str
    level: str = "basic"
    body: str = ""
    common_mistake: CommonMistake | None = None
    teaching_questions: list[str] = Field(default_factory=list)
    derived_exercise: str | None = None
    source: ExampleSource = ExampleSource.generated


class Turn(BaseModel):
    role: str
    content: str
    created_at: datetime = Field(default_factory=Timestamps.now)
