from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..context import SessionContext
from ..llm.base import LLMClient
from ..storage.attempts import AttemptStore
from ..storage.exercises import ExerciseStore
from ..storage.history import HistoryStore
from ..storage.results import ResultStore


@dataclass
class ActionServices:
    """Shared dependencies injected into every action."""

    config: Config
    context: SessionContext
    client: LLMClient | None
    data_dir: str
    history: HistoryStore = field(init=False)
    exercises: ExerciseStore = field(init=False)
    attempts: AttemptStore = field(init=False)
    results: ResultStore = field(init=False)

    def __post_init__(self) -> None:
        self.history = HistoryStore(self.data_dir)
        self.exercises = ExerciseStore(self.data_dir)
        self.attempts = AttemptStore(self.data_dir)
        self.results = ResultStore(self.data_dir)

    @classmethod
    def build(
        cls,
        config: Config,
        context: SessionContext,
        client: LLMClient | None,
    ) -> ActionServices:
        data_dir = str(config.resolved_data_dir)
        return cls(
            config=config,
            context=context,
            client=client,
            data_dir=data_dir,
        )

    def require_student(self) -> str:
        """Return the session student id or raise a user-presentable error."""
        if not self.context.student_id:
            raise LookupError(
                "no student selected; provide your name at the start of the session"
            )
        return self.context.student_id


class ActionResult:
    """Marker base for typed action results rendered by the CLI formatter."""

    def present(self) -> str:
        return ""
