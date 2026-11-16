"""Exam confirmation guidance in the TUI (RQ-EXM-003/004, RQ-TUI-013/014).

Starting or finishing an exam is consequential, so the TUI must explain what
will happen, what the exam statement needs, and exactly how to confirm or
abort before the action runs.
"""

from __future__ import annotations

import asyncio

from ada_sensei.cli.commands import (
    ErrorResponse,
    ExamineFinishCommand,
    ExamineStartCommand,
)
from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import PromptArea
from ada_sensei.config import Config
from ada_sensei.evaluation.preflight import ProjectReadiness
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
    exam = tmp_path / "exam.md"
    exam.write_text(
        "# Midterm Android Exam\n"
        "## Requirements\n"
        "- Build a screen with a list and a detail view\n",
        encoding="utf-8",
    )
    app.router.config.project.path = str(project)
    app.router.context.set_project(project)
    app.router.check_project_readiness = lambda: ProjectReadiness(str(project))
    return app, exam


def test_exam_start_prompt_explains_configuration_and_confirmation(tmp_path):
    app = _app(tmp_path)
    prompt = app._confirm_prompt(ExamineStartCommand(statement="exam.md"))

    assert "Markdown" in prompt
    assert "JSON" in prompt
    assert "PDF" in prompt
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
    prompt = app._confirm_prompt(ExamineStartCommand(statement="exam.md"))

    assert "Cómo configurar el examen" in prompt
    assert "Requisitos" in prompt
    assert "Para confirmar" in prompt
    assert "pulsa Enter" in prompt


def test_confirm_then_run_emits_the_guidance(tmp_path):
    app = _app(tmp_path)
    command = ExamineStartCommand(statement="exam.md")

    app._confirm_then_run(command)

    assert app._pending_exam is command
    assert any("How to configure the exam" in text for text in app.ui_state.messages)


def test_declining_start_aborts_with_localized_message(tmp_path):
    app = _app(tmp_path, "es-CO")
    app._confirm_then_run(ExamineStartCommand(statement="exam.md"))

    app._resolve_pending_exam(app._pending_exam, "no")

    assert app._pending_exam is None
    assert app.ui_state.status == "Listo"
    assert any("Inicio del examen cancelado" in text for text in app.ui_state.messages)


def test_confirm_button_runs_the_pending_command(tmp_path):
    app, exam = _ready_app(tmp_path)
    command = ExamineStartCommand(statement=str(exam))
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)

    app._confirm_then_run(command)
    app._confirm_pressed()

    assert ran == [command]
    assert app._pending_exam is None


def test_cancel_button_aborts_the_pending_command(tmp_path):
    app = _app(tmp_path)
    app._run_nonblocking = lambda cmd: (_ for _ in ()).throw(
        AssertionError("must not run")
    )

    app._confirm_then_run(ExamineStartCommand(statement="exam.md"))
    app._cancel_pressed()

    assert app._pending_exam is None
    assert any("aborted" in text.lower() for text in app.ui_state.messages)


def test_confirmation_bar_is_shown_with_localized_labels(tmp_path):
    app, exam = _ready_app(tmp_path, "es-CO")
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "es-CO")
            app._resolve_pending_name("s1")
            await pilot.pause()
            assert app.query_one("#confirm-bar").display is False
            app._confirm_then_run(ExamineStartCommand(statement=str(exam)))
            await pilot.pause()
            assert app.query_one("#confirm-bar").display is True
            assert "Confirmar" in str(app.query_one("#confirm-yes").label)
            assert "Cancelar" in str(app.query_one("#confirm-no").label)
            await pilot.click("#confirm-yes")
            await pilot.pause()
            assert len(ran) == 1
            assert app.query_one("#confirm-bar").display is False
            return True

    assert asyncio.run(_run())


def test_start_is_blocked_when_project_cannot_be_evaluated(tmp_path):
    # The fixture project path does not exist, so the preflight reports it.
    app = _app(tmp_path)
    result = app._dispatch_worker(
        ExamineStartCommand(statement="exam.md", yes=True)
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
        ExamineStartCommand(statement="exam.md", yes=True)
    )

    assert result == "ok"
    assert len(dispatched) == 1
    assert isinstance(dispatched[0], ExamineStartCommand)


def test_selecting_start_exam_shows_controls_immediately(tmp_path):
    app = _app(tmp_path)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            assert app.query_one("#confirm-bar").display is False

            select = app.query_one("#action-select", Select)
            select.value = "exam-init"
            await pilot.pause()

            assert app.query_one("#confirm-bar").display is True
            assert app._pending_exam is None
            assert any(
                "How to configure the exam" in text
                for text in app.ui_state.messages
            )
            return True

    assert asyncio.run(_run())


def test_confirm_without_statement_keeps_controls_open(tmp_path):
    app = _app(tmp_path)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            app.query_one("#action-select", Select).value = "exam-init"
            await pilot.pause()

            await pilot.click("#confirm-yes")
            await pilot.pause()

            assert app.query_one("#confirm-bar").display is True
            assert app._pending_exam is None
            assert any(
                "exam statement" in text.lower()
                for text in app.ui_state.messages
            )
            return True

    assert asyncio.run(_run())


def test_confirm_after_typing_statement_starts_with_it(tmp_path):
    app, exam = _ready_app(tmp_path)
    ran = []
    app._run_nonblocking = lambda cmd: ran.append(cmd)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            app.query_one("#action-select", Select).value = "exam-init"
            await pilot.pause()
            app.query_one("#input", PromptArea).text = str(exam)

            await pilot.click("#confirm-yes")
            await pilot.pause()

            assert len(ran) == 1
            assert isinstance(ran[0], ExamineStartCommand)
            assert ran[0].statement == str(exam)
            assert app.query_one("#confirm-bar").display is False
            return True

    assert asyncio.run(_run())


def test_confirm_reports_all_missing_conditions(tmp_path):
    app = _app(tmp_path)
    app.ui_state.awaiting_name = True
    app.router.context.set_student(None)

    issues = app._validate_exam_start("")
    joined = "\n".join(issues).lower()

    assert "student name" in joined
    assert "exam statement" in joined
    assert "project" in joined


def test_confirm_reports_missing_exam_instructions(tmp_path):
    app, _exam = _ready_app(tmp_path)

    issues = app._validate_exam_start(str(tmp_path / "missing.md"))

    assert any("not found" in issue.lower() for issue in issues)


def test_valid_inputs_produce_no_blocking_issues(tmp_path):
    app, exam = _ready_app(tmp_path)

    assert app._validate_exam_start(str(exam)) == []


def test_changing_action_hides_start_exam_controls(tmp_path):
    app = _app(tmp_path)

    async def _run():
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "s1", "en-US")
            app._resolve_pending_name("s1")
            await pilot.pause()
            select = app.query_one("#action-select", Select)
            select.value = "exam-init"
            await pilot.pause()
            assert app.query_one("#confirm-bar").display is True

            select.value = "ask"
            await pilot.pause()

            assert app.query_one("#confirm-bar").display is False
            return True

    assert asyncio.run(_run())
