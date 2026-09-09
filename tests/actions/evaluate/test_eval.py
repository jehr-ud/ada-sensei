from __future__ import annotations

import pytest
from ada_sensei.actions.evaluate import (
    EvalResult,
    EvaluateAction,
    EvaluateInput,
    EvaluationAborted,
    InstrumentedNotSupportedError,
)
from ada_sensei.models import Attempt, Exercise, Requirement
from helpers import FakeClient, Fixture


class OkRunner:
    """Fake subprocess runner that always succeeds."""

    def run(self, cmd, *, cwd=None, timeout=None):
        from ada_sensei.tools.subprocess import SubprocessResult

        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_s=0.1,
        )


class Fixtures:
    @staticmethod
    def make_exercise(exercise_store, student_id="student://s1"):
        exercise = Exercise(
            id="exercise://e1",
            student_id=student_id,
            project_id="project://p1",
            title="Task repository",
            objectives=["crud"],
            requirements=[
                Requirement(id="req://crud", summary="Create and list task repository")
            ],
            evaluation_criteria=[],
        )
        exercise_store.save(exercise)
        return exercise


def test_instrumented_rejected(tmp_path):
    services = Fixture.make_context(tmp_path, Fixture.build_fixture_project(tmp_path))
    with pytest.raises(InstrumentedNotSupportedError):
        EvaluateAction(services).run(EvaluateInput(instrumented=True))


def test_unconfirmed_aborts(tmp_path):
    services = Fixture.make_context(tmp_path, Fixture.build_fixture_project(tmp_path))
    with pytest.raises(EvaluationAborted):
        EvaluateAction(services).run(EvaluateInput())


def test_no_project(tmp_path):
    services = Fixture.make_context(
        tmp_path, Fixture.build_fixture_project(tmp_path), student=None
    )
    services.config.project.path = ""
    with pytest.raises(LookupError):
        EvaluateAction(services).run(EvaluateInput(confirmed=True))


def test_evaluate_with_reports(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_test_report(proj, name="TaskRepoTest", tests=5, failures=0)
    Fixture.write_lint_report(
        proj, [{"severity": "info", "message": "ns", "file": "M.kt"}]
    )
    Fixture.write_detekt_report(
        proj, [{"severity": "info", "message": "ok", "line": "1"}]
    )
    services = Fixture.make_context(
        tmp_path,
        proj,
        student="student://s1",
        client=FakeClient(),
    )
    ex = Fixtures.make_exercise(services.exercises, services.context.student_id)
    services.exercises.save(ex)
    services.context.current_exercise_id = ex.id

    result = EvaluateAction(services, runner=OkRunner()).run(
        EvaluateInput(confirmed=True)
    )
    assert isinstance(result, EvalResult)
    assert result.result.overall_score is not None
    assert isinstance(result.result.overall_score, float)
    assert result.result.exercise_id == ex.id
    assert any(c.requirement_id == "req://crud" for c in result.result.criteria)
    assert result.result.feedback
    assert result.present()


def test_build_failure_reported_as_limitation(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)

    class FailRunner:
        def run(self, cmd, *, cwd=None, timeout=None):
            from ada_sensei.tools.subprocess import SubprocessResult

            name = cmd[-1]
            exit_code = 1 if name == "assembleDebug" else 0
            return SubprocessResult(
                command=cmd,
                cwd=str(cwd),
                exit_code=exit_code,
                stdout="compilation error",
                stderr="",
                duration_s=0.1,
            )

    services = Fixture.make_context(
        tmp_path,
        proj,
        student="student://s1",
        client=FakeClient(),
    )
    ex = Fixtures.make_exercise(services.exercises, services.context.student_id)
    services.context.current_exercise_id = ex.id
    result = EvaluateAction(services, runner=FailRunner()).run(
        EvaluateInput(confirmed=True)
    )
    assert any("build" in lim.lower() for lim in result.result.limitations)


def test_persistence_and_attempt_completion(tmp_path):
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_test_report(proj, name="T", tests=1, failures=0)
    services = Fixture.make_context(
        tmp_path,
        proj,
        student="student://s1",
        client=FakeClient(),
    )
    ex = Fixtures.make_exercise(services.exercises, services.context.student_id)
    services.history.create_profile(services.context.student_id, confirmed=True)
    attempt = Attempt(
        id="attempt://a1",
        student_id=services.context.student_id,
        exercise_id=ex.id,
    )
    services.attempts.save(attempt)
    services.context.attempt_id = attempt.id

    result = EvaluateAction(services, runner=OkRunner()).run(
        EvaluateInput(confirmed=True)
    )
    persisted = services.results.get(result.result.id)
    assert persisted is not None
    attempt_after = services.attempts.get("attempt://a1")
    assert attempt_after.status == "completed"

    profile = services.history.get(services.context.student_id)
    assert profile is not None
    completed = [
        o for o in profile.events if getattr(o, "type", None) == "evaluation_completed"
    ]
    assert completed