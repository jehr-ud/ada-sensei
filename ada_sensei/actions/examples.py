from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..llm import StructuredPipeline
from ..models import (
    Difficulty,
    EvaluationCriterion,
    ExampleResult,
    ExampleSource,
    Exercise,
    ExerciseSource,
    Requirement,
)
from ..urns import URN
from .base import ActionResult, ActionServices

KNOWLEDGE_PKG = "knowledge"


class UnknownTopicError(ValueError):
    def __init__(self, topic: str, known: list[str]) -> None:
        self.topic = topic
        self.known = known
        super().__init__(
            f"unknown topic {topic!r}; known topics: {', '.join(sorted(known))}"
        )


class TopicResolver:
    def __init__(self, knowledge_root: str | Path | None = None) -> None:
        self._root = Path(knowledge_root) if knowledge_root else None

    @staticmethod
    def key(topic: str) -> str:
        return topic.lower().replace(" ", "").replace("-", "")

    def _load_taxonomy(self) -> dict[str, list[str]]:
        taxonomy = self._root / "taxonomy.toml"
        if taxonomy.is_file():
            with taxonomy.open("rb") as fh:
                data = tomllib.load(fh)
            return {
                category: list(entry.get("topics", []))
                for category, entry in data.items()
            }
        return {}

    def resolve(self, topic: str) -> tuple[str, list[str]]:
        """Return (normalized topic, known topics) or raise UnknownTopicError."""
        key = TopicResolver.key(topic)
        taxonomy = self._load_taxonomy()
        for _category, topics in taxonomy.items():
            for known in topics:
                if TopicResolver.key(known) == key:
                    return known, sorted(
                        {t for ts in taxonomy.values() for t in ts}
                    )
        namespace = sorted({t for ts in taxonomy.values() for t in ts})
        raise UnknownTopicError(topic, namespace)

    def known_topics(self) -> list[str]:
        return sorted(
            {
                t
                for ts in self._load_taxonomy().values()
                for t in ts
            }
        )


class KnowledgeRetrieval:
    def __init__(self, knowledge_root: str | Path | None = None) -> None:
        self._root = Path(knowledge_root) if knowledge_root else None

    def find_curated(self, concept: str) -> ExampleResult | None:
        if self._root is None or not self._root.is_dir():
            return None
        key = TopicResolver.key(concept)
        for json_path in sorted(self._root.rglob("*.json")):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if TopicResolver.key(str(data.get("concept") or "")) == key:
                return ExampleResult.model_validate(data)
            if TopicResolver.key(str(data.get("id") or "")).endswith(key):
                return ExampleResult.model_validate(data)
        return None


class ExamplesPrompt:
    SYSTEM = (
        "You are ADA Sensei. Generate a small, teachable Android example for the "
        "requested concept. The example must identify the concept it demonstrates "
        "and explain why the code works. Keep it small enough to explain during a "
        "lesson. Respond only with strictly valid JSON matching the ExampleResult "
        "schema. source must be \"generated\"."
    )

    @classmethod
    def messages(cls, concept: str, level: str, teacher: bool) -> list[dict[str, str]]:
        extra = ""
        if teacher:
            extra = (
                "\nAdd 2-4 teaching_questions and discussion points an instructor "
                "can use in class."
            )
        user = (
            f"Provide an example for concept: {concept!r}\n"
            f"Complexity level: {level}\n"
            "Include the concept, a body with code and explanation of why it "
            f"works, and (optionally) a flagged common mistake.{extra}"
        )
        return [{"role": "user", "content": user}]


@dataclass
class ExampleRequest:
    topic: str
    level: str = "basic"
    teacher: bool = False
    derive_exercise: bool = False


@dataclass
class ExamplesResult(ActionResult):
    example: ExampleResult

    def present(self) -> str:
        parts = [f"Concept: {self.example.concept} ({self.example.level})"]
        parts.append(self.example.body)
        if self.example.common_mistake is not None:
            parts.append(
                "Intentionally incorrect example (do NOT copy):\n"
                f"```kotlin\n{self.example.common_mistake.incorrect_code}\n```\n"
                f"Why it is wrong: {self.example.common_mistake.explanation}"
            )
        if self.example.teaching_questions:
            parts.append("Teaching questions:\n" + "\n".join(
                f"- {q}" for q in self.example.teaching_questions
            ))
        if self.example.derived_exercise:
            parts.append(f"Derived exercise: {self.example.derived_exercise}")
        return "\n\n".join(parts)


class ExamplesAction:
    def __init__(
        self,
        services: ActionServices,
        knowledge_root: str | Path | None = None,
    ) -> None:
        self.services = services
        root = (
            Path(knowledge_root)
            if knowledge_root
            else ExamplesAction.knowledge_root()
        )
        self.resolver = TopicResolver(root)
        self.retrieval = KnowledgeRetrieval(root)

    @staticmethod
    def knowledge_root() -> Path:
        """Locate the knowledge/ directory shipped with the repository."""
        return Path(__file__).resolve().parents[2] / KNOWLEDGE_PKG

    def run(
        self,
        topic: str,
        *,
        level: str = "basic",
        teacher: bool = False,
        derive_exercise: bool = False,
    ) -> ExamplesResult:
        concept, _ = self.resolver.resolve(topic)

        curated = self.retrieval.find_curated(concept)
        if curated is not None and not teacher:
            return ExamplesResult(example=curated)

        messages = ExamplesPrompt.messages(concept, level, teacher)
        pipeline = StructuredPipeline(
            self.services.client,
            max_attempts=self.services.config.llm.max_attempts,
            temperature=self.services.config.llm.temperature,
        )
        example = pipeline.run(
            messages, ExampleResult, model=self.services.config.llm.model
        )
        example.concept = concept or example.concept
        example.source = ExampleSource.generated
        example.id = URN.make("example")

        if derive_exercise:
            exercise = self._derive_exercise(example)
            saved = self.services.exercises.save(exercise)
            example.derived_exercise = saved.id

        return ExamplesResult(example=example)

    def _derive_exercise(self, example: ExampleResult) -> Exercise:
        requirement = Requirement(
            id=URN.make("req"), summary=f"implement {example.concept}"
        )
        return Exercise(
            id=URN.make("exercise"),
            title=f"Exercise around {example.concept}",
            topic=example.concept,
            difficulty=Difficulty.intermediate,
            objective=f"practice {example.concept}",
            statement=(
                f"Apply the concept '{example.concept}' to a small Android app "
                "based on the requested example."
            ),
            requirements=[requirement],
            constraints=[],
            hints=[],
            evaluation_criteria=[
                EvaluationCriterion(
                    requirement_id=requirement.id,
                    dimension="functional_requirements",
                    weight=1.0,
                )
            ],
            source=ExerciseSource.generated,
        )

    def known_topics(self) -> list[str]:
        return self.resolver.known_topics()