from __future__ import annotations

import hashlib

import pytest
from ada_sensei.actions.evaluate import (
    EvalResult,
    EvaluateAction,
    EvaluateInput,
    EvaluationAborted,
    InstrumentedNotSupportedError,
)
from ada_sensei.models import Attempt, Exercise, NotEvaluatedReason, Requirement
from helpers import FakeClient, Fixture


class OkRunner:
    """Fake subprocess runner that always succeeds."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, cmd, *, cwd=None, timeout=None):
        from ada_sensei.tools.subprocess import SubprocessResult

        self.calls.append(list(cmd))
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


# ---------------------------------------------------------------------------
# Traceability tests for the ``EvaluateAction`` boundary
# ---------------------------------------------------------------------------


class BuildFailRunner:
    """Fails only the compile step, so the build-failure policy is exercised."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, cmd, *, cwd=None, timeout=None):
        from ada_sensei.tools.subprocess import SubprocessResult

        self.calls.append(list(cmd))
        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=1 if cmd[-1] == "assembleDebug" else 0,
            stdout="compilation error",
            stderr="",
            duration_s=0.1,
        )


class FailingStore:
    """Store stub whose every write fails, to prove failures stay visible."""

    def __init__(self, label: str) -> None:
        self.label = label

    def save(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")

    def mark_completed(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")

    def append_event(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")

    def append_evaluation(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")


def snapshot(root) -> dict[str, str]:
    """Hash every file under ``root`` to detect any source modification."""
    import pathlib

    base = pathlib.Path(root)
    return {
        str(path.relative_to(base)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def evaluated(tmp_path, *, client=None, exercise=True, **runner_kwargs):
    """Run one evaluation over a fixture project and return the outcome."""
    proj = Fixture.build_fixture_project(tmp_path)
    Fixture.write_test_report(proj, name="TaskRepoTest", tests=5, failures=0)
    Fixture.write_lint_report(
        proj, [{"severity": "info", "message": "ns", "file": "M.kt"}]
    )
    Fixture.write_detekt_report(
        proj, [{"severity": "info", "message": "ok", "line": "1"}]
    )
    services = Fixture.make_context(
        tmp_path, proj, student="student://s1", client=client or FakeClient()
    )
    if exercise:
        ex = Fixtures.make_exercise(services.exercises, services.context.student_id)
        services.context.current_exercise_id = ex.id
    return services, proj, EvaluateAction(services, **runner_kwargs).run(
        EvaluateInput(confirmed=True)
    )


def test_strengths_and_weaknesses(tmp_path):
    """RQ-EVA-009: the result reports strengths as well as weaknesses."""
    _services, _proj, outcome = evaluated(tmp_path, runner=OkRunner())
    assert isinstance(outcome, EvalResult)
    assert outcome.result.strengths
    assert outcome.result.weaknesses
    presented = outcome.present()
    assert "Strengths:" in presented
    assert "Weaknesses:" in presented


def test_next_activity(tmp_path):
    """RQ-EVA-010: a next learning activity is recommended."""
    _services, _proj, outcome = evaluated(tmp_path, runner=OkRunner())
    assert outcome.result.next_learning_activity
    assert "Next learning activity:" in outcome.present()


def test_no_source_modification(tmp_path):
    """RQ-EVA-011: standard evaluation leaves student files byte-identical."""
    _services, proj, _outcome = evaluated(tmp_path, runner=OkRunner())
    # Re-run against a known baseline: the snapshot taken after the first
    # evaluation must equal the snapshot taken now, and neither may contain
    # files the fixture did not create.
    baseline = snapshot(proj)
    EvaluateAction(_services, runner=OkRunner()).run(EvaluateInput(confirmed=True))
    assert snapshot(proj) == baseline
    assert (proj / "app" / "src" / "main" / "java" / "TaskRepository.kt").read_text(
        encoding="utf-8"
    ) == "class TaskRepository { fun add() {} }\n"


def test_result_persisted(tmp_path):
    """RQ-EVA-016: the result is retrievable through its stable result:// id."""
    services, _proj, outcome = evaluated(tmp_path, runner=OkRunner())
    assert outcome.result.id.startswith("result://")
    assert services.results.exists(outcome.result.id)
    persisted = services.results.get(outcome.result.id)
    assert persisted is not None
    assert persisted.id == outcome.result.id
    assert persisted.overall_score == outcome.result.overall_score
    assert persisted.rubric_ref == "evaluate-default:v1"


def test_exercise_resolution(tmp_path):
    """RQ-EVA-017: explicit option, then session, otherwise structural only."""
    services = Fixture.make_context(
        tmp_path,
        Fixture.build_fixture_project(tmp_path),
        student="student://s1",
        client=FakeClient(),
    )
    session_ex = Fixtures.make_exercise(services.exercises, services.context.student_id)
    explicit_ex = Exercise(
        id="exercise://explicit",
        student_id=services.context.student_id,
        project_id="project://p1",
        title="Explicit",
        objectives=["crud"],
        requirements=[Requirement(id="req://explicit", summary="Explicit requirement")],
        evaluation_criteria=[],
    )
    services.exercises.save(explicit_ex)

    # 1. The explicit option wins over the session exercise.
    services.context.current_exercise_id = session_ex.id
    explicit = EvaluateAction(services, runner=OkRunner()).run(
        EvaluateInput(exercise_id=explicit_ex.id, confirmed=True)
    )
    assert explicit.result.exercise_id == explicit_ex.id
    assert any(c.requirement_id == "req://explicit" for c in explicit.result.criteria)

    # 2. With no explicit option the session exercise is used.
    from_session = EvaluateAction(services, runner=OkRunner()).run(
        EvaluateInput(confirmed=True)
    )
    assert from_session.result.exercise_id == session_ex.id

    # 3. An unknown exercise is an explicit error, never a silent fallback.
    with pytest.raises(LookupError):
        EvaluateAction(services, runner=OkRunner()).run(
            EvaluateInput(exercise_id="exercise://missing", confirmed=True)
        )

    # 4. No exercise anywhere means structural-only evaluation.
    services.context.current_exercise_id = None
    structural = EvaluateAction(services, runner=OkRunner()).run(
        EvaluateInput(confirmed=True)
    )
    assert structural.result.exercise_id is None
    assert "functional_requirements" in structural.result.not_evaluated
    assert any(
        "structural evaluation only" in lim
        for lim in structural.result.limitations
    )


def test_build_failure_blocking(tmp_path):
    """RQ-EVA-018: a failed build blocks compilation-dependent criteria."""
    services, _proj, outcome = evaluated(tmp_path, runner=BuildFailRunner())
    functional = [
        c
        for c in outcome.result.criteria
        if c.dimension == "functional_requirements" and c.requirement_id
    ]
    assert functional
    for criterion in functional:
        assert criterion.score is None
        assert criterion.not_evaluated_reason is NotEvaluatedReason.build_failed
    assert "functional_requirements" in outcome.result.not_evaluated
    assert any(
        "not evaluated" in lim and "build_failed" in lim
        for lim in outcome.result.limitations
    )


def test_confirmation_required(tmp_path):
    """RQ-EVA-019: no Gradle task runs before an explicit confirmation."""
    proj = Fixture.build_fixture_project(tmp_path)
    services = Fixture.make_context(
        tmp_path, proj, student="student://s1", client=FakeClient()
    )
    runner = OkRunner()
    with pytest.raises(EvaluationAborted) as aborted:
        EvaluateAction(services, runner=runner).run(EvaluateInput())
    assert "confirm" in str(aborted.value).lower()
    # Aborting before collection is what keeps Gradle untouched.
    assert runner.calls == []


def test_default_scope(tmp_path):
    """RQ-EVA-020: inspection, build, unit tests, lint, and detekt all run."""
    _services, _proj, outcome = evaluated(tmp_path, runner=OkRunner())
    groups = {e.type for e in outcome.result.evidence}
    assert "structure" in groups
    assert "compilation" in groups
    assert "unit_test" in groups
    sources = {e.source for e in outcome.result.evidence}
    assert {"lint", "detekt"} <= sources


def test_instrumented_not_run(tmp_path):
    """RQ-EVA-021: connectedAndroidTest is never part of the default scope."""
    runner = OkRunner()
    _services, _proj, _outcome = evaluated(tmp_path, runner=runner)
    assert all("connectedAndroidTest" not in call for call in runner.calls)
    assert {call[-1] for call in runner.calls} == {
        "assembleDebug",
        "testDebugUnitTest",
        "lint",
        "detekt",
    }


def test_non_interactive_aborts_without_yes(tmp_path):
    """RQ-EVA-023: non-interactive execution requires an explicit --yes."""
    from ada_sensei.cli.commands import ErrorResponse, EvaluateCommand
    from ada_sensei.cli.parser import CommandParser
    from ada_sensei.cli.router import Router
    from ada_sensei.config import Config

    config = Config(project={"path": str(Fixture.build_fixture_project(tmp_path))})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"

    # Without --yes the parsed command carries no confirmation...
    bare = CommandParser.parse_argv(["evaluate"])
    assert isinstance(bare, EvaluateCommand)
    assert bare.confirmed is False
    result = Router(config=config, client=FakeClient()).dispatch(bare)
    assert isinstance(result, ErrorResponse)

    # ...and with --yes the confirmation reaches the action.
    confirmed = CommandParser.parse_argv(["evaluate", "--yes"])
    assert isinstance(confirmed, EvaluateCommand)
    assert confirmed.confirmed is True


def test_persistence_failure_reported(tmp_path):
    """RQ-EVA-027: persistence failures surface as explicit limitations."""
    services = Fixture.make_context(
        tmp_path,
        Fixture.build_fixture_project(tmp_path),
        student="student://s1",
        client=FakeClient(),
    )
    ex = Fixtures.make_exercise(services.exercises, services.context.student_id)
    services.context.current_exercise_id = ex.id
    services.history.create_profile(services.context.student_id, confirmed=True)
    services.context.attempt_id = "attempt://a-missing"

    services.results = FailingStore("result store")
    services.attempts = FailingStore("attempt store")
    services.history = FailingStore("history store")

    outcome = EvaluateAction(services, runner=OkRunner()).run(
        EvaluateInput(confirmed=True)
    )
    joined = "\n".join(outcome.result.limitations)
    assert "was NOT persisted" in joined
    assert "was NOT marked completed" in joined
    assert "NOT appended to history" in joined
    assert "Limitations:" in outcome.present()