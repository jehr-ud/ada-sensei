from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMError(Exception):
    pass


class LLMClient(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def chat_structured(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> str:
        raise NotImplementedError
