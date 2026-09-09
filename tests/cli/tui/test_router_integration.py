"""TUI routes commands through the shared CommandRouter (RQ-TUI-003).

The TUI must not reimplement actions; a slash command parsed to a typed
command object dispatches to the same router the CLI uses.
"""

from __future__ import annotations

from ada_sensei.cli.commands import AskCommand, ErrorResponse
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import HELP_TEXT, AdaSenseiTUI
from ada_sensei.config import Config
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


def test_app_uses_same_router_as_cli(tmp_path):
    app = Fixtures.make_app(tmp_path)
    # The TUI dispatch is delegated to the router (no duplicate action logic).
    assert app._dispatch_worker(AskCommand("hi")) is not None
    assert isinstance(app._dispatch_worker(AskCommand("")), ErrorResponse)


def test_help_text_lists_principal_actions():
    for token in ("/practice", "/ask", "/examples", "/evaluate", "/quit"):
        assert token in HELP_TEXT
