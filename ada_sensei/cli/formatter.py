from __future__ import annotations

from ..config import Secrets
from ..llm import LLMError


class Formatter:
    """Renders action results as sanitized strings (never mutates domain state)."""

    def __init__(self, secrets: Secrets | None = None) -> None:
        self.secrets = secrets or Secrets()

    def result(self, result: object) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return self.secrets.redact(result)
        present = getattr(result, "present", None)
        if callable(present):
            rendered = present()
            return self.secrets.redact(str(rendered))
        return self.secrets.redact(str(result))

    def error(self, message: str) -> str:
        """Sanitize an error message; never expose tracebacks or secrets."""
        return self.secrets.redact(message)

    def redact(self, text: str) -> str:
        return self.secrets.redact(text)

    def sanitized(self, exception: Exception) -> str:
        """Build a safe, secret-redacted message for an unexpected error."""
        message = f"{type(exception).__name__}: {exception}"
        return self.secrets.redact(message)

    @staticmethod
    def is_llm_unavailable(exc: Exception) -> bool:
        return isinstance(exc, LLMError)