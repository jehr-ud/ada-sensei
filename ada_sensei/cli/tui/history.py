"""Session-local input prompt history (RQ-TUI-039).

Presentation/session state only: a bounded list of non-empty user-submitted
input strings for the current TUI session, plus transient navigation state
(``index``/``draft``). It never touches authoritative learning records, exam
metrics, or disk — the existing ``storage.HistoryStore`` persists student
profiles and is intentionally not reused here (different lifetime, different
privacy expectations).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Documented bound: at most this many submitted prompts are retained.
#: Older entries are dropped first. Duplicates are only deduplicated when
#: consecutive, so repeated earlier prompts remain navigable.
MAX_HISTORY_ENTRIES = 100


@dataclass
class InputHistory:
    """Bounded recall buffer for submitted input prompts."""

    max_entries: int = MAX_HISTORY_ENTRIES
    entries: list[str] = field(default_factory=list)
    index: int | None = None
    draft: str = ""

    @property
    def browsing(self) -> bool:
        """Whether history navigation is currently active."""
        return self.index is not None

    def record(self, text: str) -> bool:
        """Store a submitted input and exit navigation.

        Blank/whitespace-only submissions are ignored. A submission identical
        to the newest entry is deduplicated (returns ``False``, no duplicate
        stored). Returns whether an entry was added.
        """
        self.reset()
        cleaned = (text or "").strip()
        if not cleaned:
            return False
        if self.entries and self.entries[-1] == cleaned:
            return False
        self.entries.append(cleaned)
        del self.entries[: max(0, len(self.entries) - self.max_entries)]
        return True

    def begin(self, draft: str) -> str | None:
        """Start browsing, capturing the unsent draft; recall the newest entry.

        Returns ``None`` (and stays inactive) when history is empty.
        """
        if not self.entries:
            return None
        self.draft = draft
        self.index = len(self.entries) - 1
        return self.entries[self.index]

    def older(self) -> str | None:
        """Recall the next older entry, stopping at the oldest."""
        if self.index is None or not self.entries:
            return None
        self.index = max(0, self.index - 1)
        return self.entries[self.index]

    def newer(self) -> str:
        """Recall the next newer entry, or restore the draft past the newest.

        Restoring the draft exits navigation; the caller can observe that via
        :attr:`browsing`.
        """
        if self.index is None or not self.entries:
            return self.draft
        if self.index >= len(self.entries) - 1:
            draft = self.draft
            self.reset()
            return draft
        self.index += 1
        return self.entries[self.index]

    def reset(self) -> None:
        """Exit navigation, discarding the captured draft."""
        self.index = None
        self.draft = ""


__all__ = ["MAX_HISTORY_ENTRIES", "InputHistory"]
