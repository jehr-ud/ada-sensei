from __future__ import annotations

import pytest
from ada_sensei.llm import LLMClient, LLMError


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None) -> str:
        return "chat-output"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ) -> str:
        return '{"ok": true}'


def test_abstraction():
    client = FakeClient()
    assert isinstance(client, LLMClient)
    assert client.chat([{"role": "user", "content": "hi"}]) == "chat-output"
    assert '"ok"' in client.chat_structured([])


def test_abstract_raises():
    class Incomplete(LLMClient):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_llm_error_subclassable():
    class UpstreamError(LLMError):
        pass

    with pytest.raises(UpstreamError):
        raise UpstreamError("boom")
