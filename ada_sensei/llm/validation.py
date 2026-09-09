from __future__ import annotations

import json
from typing import Any

import jsonschema
from pydantic import BaseModel

from .base import LLMError


class InvalidJSONError(LLMError):
    pass


class LLMValidator:
    @staticmethod
    def parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.rsplit("```", 1)[0] if "```" in cleaned else cleaned
        cleaned = cleaned.strip()
        if not cleaned:
            raise InvalidJSONError("empty LLM response")
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise InvalidJSONError(f"invalid JSON from LLM: {exc.msg}") from exc
        if not isinstance(data, dict):
            raise InvalidJSONError("LLM JSON response is not an object")
        return data

    @staticmethod
    def schema_for(model_type: type[BaseModel]) -> dict[str, Any]:
        return model_type.model_json_schema()

    @staticmethod
    def validate(instance: dict[str, Any], schema: dict[str, Any]) -> None:
        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.ValidationError as exc:
            raise LLMError(f"output failed schema validation: {exc.message}") from exc
