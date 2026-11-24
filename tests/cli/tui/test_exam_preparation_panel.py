"""Preparation panel stays compact and explains blockers in the log.

RQ-EXM-033/036/038 require a compact panel whose ``Empezar examen`` option is
always reachable, plus a visible explanation of every blocker. The panel no
longer renders the variable-length blocker list (it would clip the options);
the localized reasons are emitted to the scrollable conversation log instead.
"""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import ada_sensei.cli.tui.app as app_module
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import ExamPreparationList
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient

from conftest import seed_saved_locale


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return "{}"


def _status(*blockers: str) -> SimpleNamespace:
    return SimpleNamespace(
        ready_to_start=False,
        student_ready=True,
        project_path="/tmp/project",
        instructions_path="/tmp/exam.md",
        blockers=blockers,
    )


def _render(blockers: tuple[str, ...], locale: str) -> list[str]:
    widget = ExamPreparationList()
    widget.status = _status(*blockers)
    widget.ready = False
    widget.index = 0
    widget.mode = "prepare"
    return str(widget._render_preparation(locale)).splitlines()


def test_panel_keeps_the_start_option_visible_with_many_blockers():
    many = ("no_gradle", "no_jdk", "no_android_sdk", "no_android_manifest")
    for blockers in ((), ("no_android_sdk",), many):
        lines = _render(blockers, "en-US")
        assert any("Start exam" in line for line in lines), blockers
        assert any("Back" in line for line in lines), blockers
        # Compact enough to fit the panel's max-height (14 rows).
        assert len(lines) <= 14, blockers


def test_panel_does_not_echo_raw_blocker_codes():
    lines = _render(("active_exam", "no_android_sdk"), "es-CO")
    joined = "\n".join(lines)
    assert "active_exam" not in joined
    assert "no_android_sdk" not in joined
    assert any("Empezar examen" in line for line in lines)


def _app(tmp_path, locale: str = "en-US") -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    router.context.set_student("student://s1")
    seed_saved_locale(tmp_path, "student://s1", locale)
    seed_saved_locale(tmp_path, "s1", locale)
    return AdaSenseiTUI(router=router)


def test_opening_panel_emits_localized_blocker_reasons(tmp_path):
    app = _app(tmp_path, "es-CO")
    status = _status("active_exam", "no_android_sdk")
    app.router.exam_preparation_status = lambda: status

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("s1")
            await pilot.pause()
            app._open_exam_preparation()
            await pilot.pause()
            joined = "\n".join(app.ui_state.messages)
            assert "active_exam" not in joined
            assert "no_android_sdk" not in joined
            assert "examen activo" in joined
            assert "Android SDK" in joined
            return True

    assert asyncio.run(_run())


def test_opening_panel_shows_preparing_while_worker_validates(tmp_path):
    app = _app(tmp_path, "es-CO")
    release = threading.Event()

    def _slow_status():
        release.wait(timeout=2)
        return _status("no_android_sdk")

    app.router.exam_preparation_status = _slow_status

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("s1")
            await pilot.pause()
            app._open_exam_preparation()
            await pilot.pause()

            panel = app.query_one("#exam-preparation-list", ExamPreparationList)
            assert panel.mode == "preparing"
            assert "Preparando" in str(panel._render_preparation("es-CO"))
            assert app._preparation_worker is not None

            release.set()
            await pilot.pause()
            await pilot.pause()
            assert panel.mode == "prepare"
            assert app._preparation_worker is None
            return True

    assert asyncio.run(_run())


def test_finish_opens_report_when_enabled(tmp_path, monkeypatch):
    """RQ-EXM-049: the PDF is opened with the OS viewer when enabled."""
    app = _app(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(
        app_module, "open_path", lambda path: opened.append(str(path)) or True
    )
    app.router.config.tools.open_report = True
    app._open_exam_report(SimpleNamespace(report_path="/tmp/report.pdf"))
    assert opened == ["/tmp/report.pdf"]


def test_finish_skips_open_when_disabled(tmp_path, monkeypatch):
    app = _app(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(
        app_module, "open_path", lambda path: opened.append(str(path)) or True
    )
    app.router.config.tools.open_report = False
    app._open_exam_report(SimpleNamespace(report_path="/tmp/report.pdf"))
    assert opened == []


def test_reopening_panel_does_not_repeat_same_blockers(tmp_path):
    app = _app(tmp_path, "en-US")
    app.router.exam_preparation_status = lambda: _status("no_android_sdk")

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("s1")
            await pilot.pause()
            app._open_exam_preparation()
            await pilot.pause()
            first = list(app.ui_state.messages)
            app._open_exam_preparation()
            await pilot.pause()
            assert app.ui_state.messages == first
            return True

    assert asyncio.run(_run())
