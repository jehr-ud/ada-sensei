from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import LLMClient, LLMError

DEFAULT_BASE_URL = "http://localhost:11434/v1"


class OllamaProvider(LLMClient):
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        api_key: str | None = None,
        timeout_seconds: int = 120,
        temperature: float = 0.2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, path: str, payload: dict, timeout: int | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout or self.timeout_seconds
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMError(f"ollama http error {exc.code}: {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(f"ollama request failed: {exc}") from exc

    def _get(self, path: str, timeout: int | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        request = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(
                request, timeout=timeout or self.timeout_seconds
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMError(f"ollama http error {exc.code}: {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(f"ollama request failed: {exc}") from exc

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        response = self._post(
            "chat/completions", self._payload(messages, model, temperature)
        )
        choices = response.get("choices") or []
        if not choices:
            raise LLMError(f"ollama chat returned no choices: {response}")
        content = choices[0].get("message", {}).get("content")
        if content is None:
            raise LLMError("ollama chat returned empty content")
        return content

    def chat_structured(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        payload = self._payload(messages, model, temperature)
        payload["format"] = "json"
        if json_schema:
            payload["response_format"] = {"type": "json_object"}
        response = self._post("chat/completions", payload)
        choices = response.get("choices") or []
        if not choices:
            raise LLMError(f"ollama structured call returned no choices: {response}")
        return choices[0].get("message", {}).get("content") or ""

    def _payload(
        self,
        messages: list[dict[str, str]],
        model: str | None,
        temperature: float | None,
    ) -> dict:
        return {
            "model": model or "qwen2.5-coder:7b",
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }

    def list_models(self) -> list[str]:
        data = self._get("models")
        return [m.get("name") for m in data.get("data", [])]

    def server_available(self, timeout: float = 2.0) -> bool:
        try:
            self._get("models", timeout=timeout)
            return True
        except LLMError:
            return False
