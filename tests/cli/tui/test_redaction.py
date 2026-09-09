"""Error handling and secret redaction in the TUI (RQ-TUI-019 / 020).

Expected errors render as messages without stack traces; secrets are never
shown in output or diagnostics.
"""

from __future__ import annotations

from ada_sensei.cli.commands import ErrorResponse
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.config import Config, Secrets
from ada_sensei.llm.base import LLMClient


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        from ada_sensei.models import Answer

        return Answer(id="answer://a1", response="hello").model_dump_json()


class Fixtures:
    @staticmethod
    def make_app(tmp_path) -> AdaSenseiTUI:
        config = Config(project={"path": str(tmp_path / "p")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        router = Router(config=config, client=FakeClient())
        return AdaSenseiTUI(router=router)


def test_error_response_renders_no_stacktrace(tmp_path):
    app = Fixtures.make_app(tmp_path)
    rendered = app.formatter.error(ErrorResponse("bad input").message)
    assert "Traceback" not in rendered
    assert "bad input" in rendered


def test_secret_redacted_in_tui_formatter():
    from ada_sensei.cli.formatter import Formatter as Fmt

    secrets = Secrets(
        env={"ADA_SENSEI_API_KEY": "TOPSECRET"},
        defaults={"api_key_env": "ADA_SENSEI_API_KEY"},
    )
    fmt = Fmt(secrets)
    out = fmt.error("failed with TOPSECRET token")
    assert "TOPSECRET" not in out
    assert "***" in out
