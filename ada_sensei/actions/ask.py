from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..context import MAX_TURNS
from ..llm import StructuredPipeline
from ..models import Answer, AssistanceLevel, LearningEvent, Turn
from ..tools.inspector import ProjectInspector
from .base import ActionResult, ActionServices

CLASSIFICATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "debugging": (
        "error",
        "crash",
        "exception",
        "bug",
        "doesn't work",
        "does not work",
        "not update",
        "warning",
        "crashes",
        "fails",
        "stack trace",
    ),
    "implementation": (
        "implement",
        "how do i",
        "how to",
        "write",
        "code",
        "function",
        "snippet",
        "example code",
    ),
    "architecture": (
        "architecture",
        "pattern",
        "architecture pattern",
        "mvvm",
        "mvi",
        "clean",
        "module",
        "layer",
        "dependency",
    ),
    "tooling": (
        "gradle",
        "sdk",
        "build",
        "detekt",
        "lint",
        "plugin",
        "kapt",
        "ksp",
    ),
    "testing": (
        "test",
        "testing",
        "junit",
        "robolectric",
        "mock",
        "assert",
    ),
    "conceptual": (
        "what",
        "why",
        "explain",
        "difference",
        "concept",
        "state",
        "lifecycle",
        "composable",
    ),
}


class QuestionClassifier:
    def classify(self, question: str) -> str:
        lowered = question.lower()
        for category, keywords in CLASSIFICATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in lowered:
                    return category
        return "conceptual"

    def needs_project_inspection(self, category: str) -> bool:
        return category == "debugging"


class ContextBuilder:
    def __init__(
        self,
        services: ActionServices,
        project_path: str | None = None,
        inspector: ProjectInspector | None = None,
    ) -> None:
        self.services = services
        self.project_path = project_path
        self._inspector = inspector

    def _inspector_for(self, project_path: str) -> ProjectInspector | None:
        if self._inspector is not None:
            return self._inspector
        path = Path(project_path).expanduser()
        if not path.is_dir():
            return None
        try:
            return ProjectInspector(path)
        except (FileNotFoundError, PermissionError):
            return None

    def build(
        self, question: str, classification: str
    ) -> dict[str, object]:
        ctx: dict[str, object] = {"conversation": self.services.context.conversation}
        profile = None
        if self.services.context.student_id:
            profile = self.services.history.get(self.services.context.student_id)
        ctx["student_summary"] = (
            profile.summary if profile is not None else "(no profile)"
        )

        excerpts: list[str] = []
        if classification == "debugging" and self.project_path:
            inspector = self._inspector_for(str(self.project_path))
            if inspector is not None:
                excerpts = self._file_excerpts(inspector, question)
        ctx["file_excerpts"] = excerpts
        return ctx

    def _file_excerpts(
        self, inspector: ProjectInspector, question: str, limit: int = 4
    ) -> list[str]:
        results: list[str] = []
        for rel in self._relevant_files(inspector, question, limit):
            content = inspector.read_file(rel)
            if content:
                results.append(f"--- {rel} ---\n{content[:1200]}")
        return results

    def _relevant_files(
        self, inspector: ProjectInspector, question: str, limit: int = 4
    ) -> list[str]:
        candidates = inspector.list_source_files()
        lowered = question.lower()
        keywords = {word for word in lowered.split() if len(word) > 4}
        scored: list[tuple[int, str]] = []
        for rel in candidates:
            score = sum(1 for kw in keywords if kw in rel.lower())
            scored.append((score, rel))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [rel for _, rel in scored if _ > 0][:limit]


class TutorAgent:
    SYSTEM = (
        "You are ADA Sensei, an Android development tutor. Answer the student's "
        "question pedagogically. Prefer explanations that promote understanding "
        "over complete code dumps unless the assistance level asks for it. "
        "For project-specific claims, cite the relevant file (and line where "
        "known). If available evidence is insufficient, state uncertainty "
        "explicitly instead of guessing. Never claim evidence you do not have. "
        "Respond only with strictly valid JSON matching the Answer schema."
    )

    def __init__(self, services: ActionServices) -> None:
        self.services = services

    def answer(
        self,
        question: str,
        classification: str,
        context: dict[str, object],
        assistance_level: AssistanceLevel,
    ) -> Answer:
        messages = self._messages(question, classification, context, assistance_level)
        pipeline = StructuredPipeline(
            self.services.client,
            max_attempts=self.services.config.llm.max_attempts,
            temperature=self.services.config.llm.temperature,
        )
        answer = pipeline.run(
            messages, Answer, model=self.services.config.llm.model
        )
        reply = Answer(
            id=answer.id,
            question=question,
            classification=classification,
            assistance_level=assistance_level,
            response=answer.response,
            citations=answer.citations,
            uncertainty=answer.uncertainty,
        )
        return reply

    def _messages(
        self,
        question: str,
        classification: str,
        context: dict[str, object],
        assistance_level: AssistanceLevel,
    ) -> list[dict[str, str]]:
        turns: list[Turn] = context.get("conversation", [])
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.SYSTEM}
        ]
        for turn in turns[-MAX_TURNS:]:
            messages.append({"role": turn.role, "content": turn.content})

        excerpts: list[str] = list(context.get("file_excerpts") or [])
        file_block = "\n\n".join(excerpts)

        student = context.get("student_summary", "(no profile)")
        user = (
            f"Question classification: {classification}\n"
            f"Assistance level: {assistance_level.value}\n"
            f"Student context: {student}\n"
            f"Question: {question}\n\n"
        )
        if file_block:
            user += "Relevant project files:\n" + file_block + "\n\n"
        user += (
            "Answer using exactly the Answer schema: question, classification, "
            "assistance_level, response, citations (file:line refs), uncertainty "
            "(true only when evidence is insufficient)."
        )
        messages.append({"role": "user", "content": user})
        return messages


class EscalationRequest(Exception):
    pass


@dataclass
class AskResult(ActionResult):
    answer: Answer

    def present(self) -> str:
        parts = [self.answer.response]
        if self.answer.citations:
            parts.append("Evidence: " + ", ".join(self.answer.citations))
        if self.answer.uncertainty:
            parts.append(
                "(Note: available evidence was insufficient; this answer states "
                "uncertainty where it applies.)"
            )
        return "\n\n".join(parts)


class AskAction:
    def __init__(self, services: ActionServices) -> None:
        self.services = services
        self.classifier = QuestionClassifier()
        self.builder = ContextBuilder(services)

    def run(self, question: str) -> AskResult:
        if not question.strip():
            raise ValueError("ask requires a question")
        return self._answer(question, classify=True)

    def escalate(self, command: str) -> AskResult:
        """Re-answer the last question at the advanced assistance level."""
        turn = self._last_user_turn()
        if turn is None:
            raise LookupError("no question in the current conversation to escalate")
        if command == "hint":
            self.services.context.assistance_level = AssistanceLevel.hint
        elif command == "solution":
            self.services.context.assistance_level = AssistanceLevel.solution
        else:
            self.services.context.advance_assistance()
        return self._answer(turn.content, classify=False, record=False)

    def _answer(self, question: str, classify: bool, record: bool = True) -> AskResult:
        classification = (
            self.classifier.classify(question)
            if classify
            else (self.services.context.last_classification or "conceptual")
        )
        ctx = self.builder.build(question, classification)
        answer = TutorAgent(self.services).answer(
            question,
            classification,
            ctx,
            self.services.context.assistance_level,
        )
        if record:
            self.services.context.last_classification = classification
            self.services.context.add_turn("user", question)
            self.services.context.add_turn("assistant", answer.response)
            if self.services.context.student_id:
                self.services.history.append_event(
                    self.services.context.student_id,
                    LearningEvent(
                        type="question_asked",
                        exercise_id=self.services.context.current_exercise_id,
                        payload={
                            "question": question,
                            "classification": classification,
                        },
                    ),
                )
        return AskResult(answer=answer)

    def _last_user_turn(self) -> Turn | None:
        for turn in reversed(self.services.context.conversation):
            if turn.role == "user":
                return turn
        return None