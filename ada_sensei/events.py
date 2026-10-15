"""Application event bus (RQ-EXM-005, RQ-EXM-031).

The exam counter must not depend on the TUI, the direct CLI, or terminal text, so
workflows publish plain application events and observers subscribe. ``AskAction``
emits ask events; ``ExamEventBridge`` counts them. Neither imports the other, and
neither parses output text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

#: Event names published by application workflows. Free-form strings, but these
#: are the ones the exam subscribes to.
ASK_STARTED = "ask.started"
ASK_COMPLETED = "ask.completed"
ASK_FAILED = "ask.failed"
ASK_CANCELLED = "ask.cancelled"


@dataclass(frozen=True)
class AppEvent:
    """One published application event."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)


class AppEventBus:
    """Minimal synchronous publish/subscribe bus.

    A handler failure is isolated: one broken subscriber must not break the
    workflow that published the event.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[AppEvent], None]]] = {}
        self._errors: list[tuple[str, Exception]] = []

    def subscribe(
        self, event_type: str, handler: Callable[[AppEvent], None]
    ) -> Callable[[AppEvent], None]:
        self._subscribers.setdefault(event_type, []).append(handler)
        return handler

    def unsubscribe(self, event_type: str, handler: Callable[[AppEvent], None]) -> None:
        handlers = self._subscribers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def emit(self, event: AppEvent) -> None:
        for handler in list(self._subscribers.get(event.type, ())):
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - observers must not break
                # the publishing workflow; the failure is kept for inspection.
                self._errors.append((event.type, exc))

    def errors(self) -> list[tuple[str, Exception]]:
        return list(self._errors)

    def subscriber_count(self, event_type: str | None = None) -> int:
        if event_type is None:
            return sum(len(h) for h in self._subscribers.values())
        return len(self._subscribers.get(event_type, ()))


__all__ = [
    "ASK_CANCELLED",
    "ASK_COMPLETED",
    "ASK_FAILED",
    "ASK_STARTED",
    "AppEvent",
    "AppEventBus",
]
