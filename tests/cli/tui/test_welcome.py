"""TUI welcome identity (RQ-TUI-029, RQ-TUI-007).

The name the student provides at the welcome greeting IS the student identity:
it is bound to the session and persisted to the StudentProfile. Returning
profiles are greeted with "Welcome back".
"""

from __future__ import annotations

from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient
from ada_sensei.storage.history import HistoryStore


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


def test_name_becomes_identity(tmp_path):
    app = Fixtures.make_app(tmp_path)
    app._resolve_pending_name("Bob")
    assert app.router.context.student_id == "Bob"
    assert app.ui_state.user_name == "Bob"
    assert app.ui_state.awaiting_name is False


def test_profile_created_from_name(tmp_path):
    app = Fixtures.make_app(tmp_path)
    app._resolve_pending_name("Carol")
    store = HistoryStore(str(tmp_path))
    assert store.has("Carol")
    assert store.get("Carol").name == "Carol"


def test_new_profile_greeted_and_persisted(tmp_path):
    app = Fixtures.make_app(tmp_path)
    captured = []
    app._emit = lambda text: captured.append(text)
    app._resolve_pending_name("Dana")
    assert any("Welcome" in text for text in captured)
    assert any("Dana" in text for text in captured)
    assert not any("back" in text for text in captured)


def test_returning_profile_welcome_back(tmp_path):
    store = HistoryStore(str(tmp_path))
    store.create_profile("alice", confirmed=True)
    store.set_name("alice", "alice")
    app = Fixtures.make_app(tmp_path)
    captured = []
    app._emit = lambda text: captured.append(text)
    app._resolve_pending_name("alice")
    assert any("Welcome back" in text for text in captured)


def test_identity_not_inferred_from_greeting(tmp_path):
    app = Fixtures.make_app(tmp_path)
    captured = []
    app._emit = lambda text: captured.append(text)
    app._resolve_pending_name("  ")
    assert app.ui_state.awaiting_name is True
    assert app.router.context.student_id is None
    assert any("didn't catch" in text for text in captured)