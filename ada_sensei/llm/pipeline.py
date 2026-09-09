from __future__ import annotations

from copy import deepcopy
from typing import TypeVar

import pydantic
from pydantic import BaseModel

from .base import LLMClient, LLMError
from .validation import InvalidJSONError, LLMValidator

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(LLMError):
    pass


class StructuredPipeline:
    def __init__(
        self, client: LLMClient, *, max_attempts: int = 3, temperature: float = 0.2
    ) -> None:
        if not 1 <= max_attempts <= 3:
            raise ValueError(
                "max_attempts must be between 1 and 3 "
                "(1 initial attempt + up to 2 retries)"
            )
        self.client = client
        self.max_attempts = max_attempts
        self.temperature = temperature

    @staticmethod
    def run_structured(
        client: LLMClient,
        messages: list[dict[str, str]],
        model_type: type[T],
        *,
        model: str | None = None,
        max_attempts: int = 3,
    ) -> T:
        return StructuredPipeline(client, max_attempts=max_attempts).run(
            messages, model_type, model=model
        )

    def run(
        self,
        messages: list[dict[str, str]],
        model_type: type[T],
        *,
        model: str | None = None,
    ) -> T:
        schema = LLMValidator.schema_for(model_type)
        work = deepcopy(messages)
        work.insert(
            0,
            {
                "role": "system",
                "content": (
                    "Respond with strictly valid JSON conforming to the supplied "
                    "schema. Do not wrap the JSON in markdown fences."
                ),
            },
        )

        last_error: str | None = None
        for attempt in range(self.max_attempts):
            raw = self.client.chat_structured(
                work, model=model, json_schema=schema, temperature=self.temperature
            )
            try:
                data = LLMValidator.parse_json(raw)
                LLMValidator.validate(data, schema)
                return model_type.model_validate(data)
            except (InvalidJSONError, LLMError, pydantic.ValidationError) as exc:
                last_error = str(exc).splitlines()[0]
            if attempt < self.max_attempts - 1:
                work.append({"role": "assistant", "content": raw})
                work.append(
                    {
                        "role": "user",
                        "content": f"Your previous output was rejected: {last_error}. "
                        "Return only corrected JSON matching the schema.",
                    }
                )

        raise StructuredOutputError(
            f"structured output failed after {self.max_attempts} total "
            f"attempt(s): {last_error}"
        )
