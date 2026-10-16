"""GUI selector + stage header + version + locale integration (RQ-TUI-035/036/037/038).

- Every registry action appears in the selector and routes to its workflow.
- Header shows the real stage + installed version; footer repeats them.
- Switching locale relabels without resetting progress.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ada_sensei.cli.action_registry import get_actions
from ada_sensei.cli.commands import (
    AskCommand,
    DiagnoseCommand,
    EvaluateCommand,
    ExamineFinishCommand,
    ExamineStartCommand,
    ExamplesCommand,
    HelpCommand,
    LanguageCommand,
    LearnCommand,
    PracticeCommand,
)
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI, localized_action_options
from ada_sensei.cli.tui.widgets import SessionFooter
from ada_sensei.config import Config
from ada_sensei.learning.models import LearningProfile
from ada_sensei.learning.stores import LearningProfileStore
from ada_sensei.llm.base import LLMClient
from ada_sensei.locale.service import LocaleService
from ada_sensei.locale.store import LocalePreferenceStore
from ada_sensei.version import get_app_version
from textual.widgets import Select


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(self, messages, *, model=None, json_schema=None, temperature=None):
        from ada_sensei.models import Answer

        return Answer(id="answer://a1", response="hello").model_dump_json()


def make_app(tmp_path) -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    return AdaSenseiTUI(router=router)


def mounted(tmp_path, fn):
    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def _seed_profile(tmp_path, stage="state-basic-architecture"):
    now = datetime.now(tz=UTC)
    LearningProfileStore(str(tmp_path)).save(
        LearningProfile(
            student_id="Ada",
            catalog_id="android-learning-path",
            catalog_version="1.2.0",
            current_stage_id=stage,
            created_at=now,
            updated_at=now,
        )
    )


def test_every_registry_action_in_selector(tmp_path):
    ids = {value for _, value in localized_action_options("en-US")}
    assert ids == {a.id for a in get_actions()}
    assert len(ids) == 10

    async def check(app, pilot):
        select = app.query_one("#action-select", Select)
        assert select is not None
        # options carry localized labels; values are the stable ids
        option_values = [v for _, v in localized_action_options("en-US")]
        assert set(option_values) == {a.id for a in get_actions()}
        return True

    assert mounted(tmp_path, check)


def test_each_action_routes_to_correct_workflow(tmp_path):
    async def check(app, pilot):
        cases = {
            "ask": (AskCommand, "why?"),
            "practice": (PracticeCommand, "compose-state"),
            "examples": (ExamplesCommand, "ViewModel"),
            "evaluate": (EvaluateCommand, ""),
            "exam-init": (ExamineStartCommand, "docs/exam.md"),
            "exam-finish": (ExamineFinishCommand, ""),
            "learn": (LearnCommand, ""),
            "diagnose": (DiagnoseCommand, ""),
            "language": (LanguageCommand, "es-CO"),
            "help": (HelpCommand, ""),
        }
        for action_id, (expected, text) in cases.items():
            app.ui_state.action = action_id
            cmd = app._command_from_line(text if text else _empty_for(action_id))
            assert isinstance(cmd, expected), action_id
        return True

    assert mounted(tmp_path, check)


def _empty_for(action_id: str) -> str:
    return ""


def test_spanish_labels_and_stage_header(tmp_path):
    _seed_profile(tmp_path)
    svc = LocaleService(LocalePreferenceStore(str(tmp_path)))
    svc.set_locale("Ada", "es-CO")

    async def check(app, pilot):
        app.router.context.set_student("Ada")
        app._refresh_selector_labels()
        app.refresh_session_bar()
        await pilot.pause()
        bar = str(app.query_one("#session-bar").renderable)
        assert get_app_version() in bar
        assert "Etapa actual: 5" in bar
        footer = str(app.query_one("#session-footer", SessionFooter).renderable)
        assert "Etapa actual: 5" in footer
        assert get_app_version() in footer
        assert "Lang: es-CO" in footer
        return True

    assert mounted(tmp_path, check)


def test_language_switch_preserves_progress(tmp_path):
    _seed_profile(tmp_path, stage="kotlin-fundamentals")

    async def check(app, pilot):
        app.router.context.set_student("Ada")
        before = app.router.learning_stage().stage_id
        app.router.dispatch(LanguageCommand(locale="en-US"))
        app._refresh_selector_labels()
        app.refresh_session_bar()
        after = app.router.learning_stage().stage_id
        assert before == after == "kotlin-fundamentals"
        footer = str(app.query_one("#session-footer", SessionFooter).renderable)
        assert "Lang: en-US" in footer
        return True

    assert mounted(tmp_path, check)


def test_unavailable_action_explains_prerequisite(tmp_path):
    async def check(app, pilot):
        app.router.config.project.path = ""
        app.router.context.set_project(None)
        explained = app._check_availability(EvaluateCommand())
        assert explained
        return True

    assert mounted(tmp_path, check)


def test_busy_guard_blocks_duplicates(tmp_path):
    async def check(app, pilot):
        app.ui_state.set_busy(True, "Running")
        emitted: list[str] = []
        app._emit = lambda text: emitted.append(text)  # type: ignore[method-assign]
        app._handle_command(AskCommand(question="hello?"))
        assert emitted  # blocked message shown, no dispatch
        return True

    assert mounted(tmp_path, check)
