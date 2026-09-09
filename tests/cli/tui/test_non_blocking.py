"""Non-blocking operations (RQ-TUI-016 / 017).

Long-running work must go through a Textual worker so the UI event loop is not
blocked, and cancellation must be propagated to the worker.
"""

from __future__ import annotations

from ada_sensei.cli.commands import AskCommand
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
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


def test_run_nonblocking_uses_worker(tmp_path):
    app = Fixtures.make_app(tmp_path)
    captured = {}

    def fake_run_worker(func, **kw):
        captured["func"] = func
        return _FakeWorker()

    app.run_worker = fake_run_worker
    app._run_nonblocking(AskCommand("hi"))
    assert captured["func"] is not None
    assert app.ui_state.busy is True


def test_cancel_propagates_to_worker(tmp_path):
    app = Fixtures.make_app(tmp_path)

    class W:
        is_cancelled = False

        def cancel(self):
            self.is_cancelled = True

    worker = W()
    app._active_worker = worker
    app.action_cancel_operation()
    assert worker.is_cancelled is True
    assert app.ui_state.busy is False


class _FakeWorker:
    is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def add_done_callback(self, fn):
        self.done = fn
