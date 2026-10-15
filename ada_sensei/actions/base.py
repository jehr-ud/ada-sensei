from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..context import SessionContext
from ..events import AppEventBus
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
    #: Process-wide application events; ``/ask`` publishes and the exam
    #: subscribes, so the exam counter never parses terminal text
    #: (RQ-EXM-006).
    event_bus: AppEventBus = field(init=False)

    def __post_init__(self) -> None:
        self.history = HistoryStore(self.data_dir)
        self.exercises = ExerciseStore(self.data_dir)
        self.attempts = AttemptStore(self.data_dir)
        self.results = ResultStore(self.data_dir)
        self.event_bus = AppEventBus()

    @classmethod
    def build(
        cls,
        config: Config,
        context: SessionContext,
        client: LLMClient | None,
        event_bus: AppEventBus | None = None,
    ) -> ActionServices:
        """Build the shared dependencies for one action invocation.

        ``event_bus`` must be the *session* bus, not a fresh one: the exam
        subscribes to ``/ask`` events across separate action invocations, so a
        per-call bus would drop the subscription the moment the action that
        created it returned (RQ-EXM-005, RQ-EXM-031).
        """
        data_dir = str(config.resolved_data_dir)
        services = cls(
            config=config,
            context=context,
            client=client,
            data_dir=data_dir,
        )
        if event_bus is not None:
            services.event_bus = event_bus
        return services

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
