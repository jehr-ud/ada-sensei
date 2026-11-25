"""Exam start uses the compact preparation list instead of Confirm/Cancel.

RQ-EXM-033/036/038 require a keyboard-navigable panel with a visible
``Empezar examen`` option, localized reasons for every blocker, and no large
buttons. The shared confirm bar remains only for Gradle evaluation.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from ada_sensei.cli.commands import (
    ErrorResponse,
    ExamineFinishCommand,
    ExamineStartCommand,
)
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import ExamPreparationList
from ada_sensei.config import Config
from ada_sensei.evaluation.preflight import ProjectReadiness
from ada_sensei.exams.preparation import ExamPreparationService
from ada_sensei.llm.base import LLMClient
from textual.widgets import Select

from conftest import seed_saved_locale


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return "{}"


def _app(tmp_path, locale: str = "en-US") -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    router.context.set_student("student://s1")
    seed_saved_locale(tmp_path, "student://s1", locale)
    return AdaSenseiTUI(router=router)


def _ready_app(tmp_path, locale: str = "en-US"):
    """App fixture with a valid exam statement and a ready project."""
    app = _app(tmp_path, locale)
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    exam = tmp_path / "exam.json"
    exam.write_text(
        """{
  "schema_version": "1.0",
  "exam_id": "midterm-android-exam",
  "title": "Midterm Android Exam",
  "version": "1.0",
  "allowed_duration_seconds": 3600,
  "allowed_ask_count": 4,
  "rubric_ref": "unified-android:v2",
  "requirements": [
    {
      "id": "REQ-MID-001",
      "type": "functional",
      "title": "Screen",
      "description": "Build a screen with a list and a detail view",
      "weight": 1.0,
      "source": {"file": "midterm-android-exam.json", "section": "Requirements"},
      "acceptance_criteria": [
        {
          "id": "AC-MID-001",
          "description": "Screen works.",
          "verification": ["ui_inspection"]
        }
      ]
    }
  ]
}""",
        encoding="utf-8",
    )
    app.router.config.project.path = str(project)
    app.router.context.set_project(project)
    app.router.check_project_readiness = lambda: ProjectReadiness(str(project))
    return app, exam


def _status(*, ready: bool = False, instructions_path: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        ready_to_start=ready,
        student_ready=True,
        project_path="/tmp/project",
        project_ready=ready,
        project_blockers=() if ready else ("no_project",),
        instructions_path=instructions_path or "/tmp/exam.json",
        exam_definition_path=instructions_path or "/tmp/exam.json",
        instructions_ready=ready,
        instruction_blockers=() if ready else ("no_instructions",),
        active_exam=False,
        blockers=() if ready else ("no_project", "no_instructions"),
        toolchain_ready=ready,
        toolchain_blockers=(),
    )


def test_preparation_service_reports_localized_stage_progress(tmp_path, monkeypatch):
    app = _app(tmp_path, "es-CO")
    project = tmp_path / "project"
    project.mkdir()
    app.router.config.project.path = str(project)
    app.router.context.set_project(project)
    monkeypatch.setattr(
        "ada_sensei.exams.preparation.ProjectPreflight.check",
        lambda _self, _path: ProjectReadiness(str(project)),
    )

    class FakeToolchain:
        def prepare(self, _path):
            return SimpleNamespace(
                ready=True, blockers=(), manifest=None, executions=()
            )

    messages: list[str] = []
    service = ExamPreparationService(
        app.router.services(), toolchain=FakeToolchain(), progress=messages.append
    )

    service.validate(require_instructions=False, locale="es-CO")

    assert messages[0] == "Validando requisitos del examen…"
    assert "Preparando herramientas de análisis estático" in messages[1]


def test_exam_start_prompt_explains_configuration_and_confirmation(tmp_path):
    app = _app(tmp_path)
    prompt = app._confirm_prompt(ExamineStartCommand(statement="exam.json"))

    assert "JSON" in prompt
    assert "Markdown" not in prompt
    assert "PDF" not in prompt
    assert "title" in prompt.lower()
    assert "requirements" in prompt.lower()
    assert "Allowed duration" in prompt
    assert "Allowed /ask count" in prompt
    assert "yes" in prompt and "Enter" in prompt
    assert "no" in prompt


def test_exam_finish_prompt_explains_confirmation(tmp_path):
    app = _app(tmp_path)
    prompt = app._confirm_prompt(ExamineFinishCommand())

    assert "timer" in prompt.lower()
    assert "PDF report" in prompt
    assert "yes" in prompt and "Enter" in prompt
    assert "no" in prompt


def test_exam_start_prompt_is_localized(tmp_path):
    app = _app(tmp_path, "es-CO")
    prompt = app._confirm_prompt(ExamineStartCommand(statement="exam.json"))

    assert "Cómo configurar el examen" in prompt
    assert "Requisitos" in prompt
    assert "Para confirmar" in prompt
    assert "pulsa Enter" in prompt


def test_start_is_blocked_when_project_cannot_be_evaluated(tmp_path):
    app = _app(tmp_path)
    result = app._dispatch_worker(
        ExamineStartCommand(statement="exam.json", yes=True)
    )

    assert isinstance(result, ErrorResponse)
    assert "cannot be evaluated" in result.message
    assert "does not exist" in result.message


def test_start_proceeds_when_project_is_ready(tmp_path):
    app = _app(tmp_path)
    app.router.check_project_readiness = lambda: ProjectReadiness("/proj")
    dispatched = []
    app.router.dispatch = lambda cmd: dispatched.append(cmd) or "ok"

    result = app._dispatch_worker(
        ExamineStartCommand(statement="exam.json", yes=True)
    )

    assert result == "ok"
    assert len(dispatched) == 1
    assert isinstance(dispatched[0], ExamineStartCommand)


def test_selecting_start_exam_shows_only_the_compact_panel(tmp_path):
    app = _app(tmp_path)
    app.router.exam_preparation_status = lambda: _status()

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            assert app.query_one("#confirm-bar").display is False

            app.query_one("#action-select", Select).value = "exam-init"
            await pilot.pause()

            assert app.query_one("#confirm-bar").display is False
            panel = app.query_one("#exam-preparation-list", ExamPreparationList)
            assert panel.display is True
            assert "Start exam" in str(panel._render_preparation("en-US"))
            assert app._pending_exam is None

            joined = "\n".join(app.ui_state.messages).lower()
            assert "/project" in joined
            assert "/instructions" in joined
            return True

    assert asyncio.run(_run())


def test_blocked_start_repeats_actionable_guidance_and_runs_nothing(tmp_path):
    app = _app(tmp_path)
    app.router.exam_preparation_status = lambda: _status()
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            app._open_exam_preparation()
            await pilot.pause()
            before = len(app.ui_state.messages)

            app.on_exam_preparation_confirmed(ExamPreparationList.Confirmed("start"))
            await pilot.pause()

            assert ran == []
            assert len(app.ui_state.messages) > before
            assert app.query_one("#confirm-bar").display is False
            joined = "\n".join(app.ui_state.messages[before:])
            assert "cannot start yet" in joined
            assert "/project" in joined
            assert "/instructions" in joined
            return True

    assert asyncio.run(_run())


def test_ready_panel_starts_exam_without_confirm_buttons(tmp_path):
    app, exam = _ready_app(tmp_path)
    app.router.exam_preparation_status = lambda: _status(
        ready=True, instructions_path=str(exam)
    )
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            app._open_exam_preparation()
            await pilot.pause()

            app.on_exam_preparation_confirmed(ExamPreparationList.Confirmed("start"))
            await pilot.pause()

            assert len(ran) == 1
            assert isinstance(ran[0], ExamineStartCommand)
            assert ran[0].statement == str(exam)
            assert ran[0].confirmed is True
            assert app.query_one("#confirm-bar").display is False
            return True

    assert asyncio.run(_run())


def test_changing_action_closes_the_preparation_panel(tmp_path):
    app = _app(tmp_path)
    app.router.exam_preparation_status = lambda: _status()

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            select = app.query_one("#action-select", Select)
            select.value = "exam-init"
            await pilot.pause()
            assert app.query_one("#exam-preparation-list").display is True

            select.value = "ask"
            await pilot.pause()

            assert app.query_one("#exam-preparation-list").display is False
            assert app.query_one("#confirm-bar").display is False
            return True

    assert asyncio.run(_run())
