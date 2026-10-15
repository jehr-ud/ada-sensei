"""RQ-EXM-010/011/012/028: exam overlay over the shared evaluation engine."""

from __future__ import annotations

import json

import pytest
from ada_sensei.actions.examine import (
    ExamFinishInput,
    ExamFinishResult,
    ExamineAction,
    ExamStartInput,
    InstrumentedNotSupportedError,
)
from ada_sensei.exams.models import ExamDefinitionError
from ada_sensei.exams.rubric import EXAM_RUBRIC, resolve_rubric
from ada_sensei.exams.scoring import ExamScorer
from ada_sensei.llm.base import LLMClient
from exams_helpers import (
    OkRunner,
    make_context,
    make_definition,
    make_evidence,
    make_project,
)

STATEMENT = (
    "# Midterm Android Exam\n"
    "\n"
    "Allowed duration: 60 minutes\n"
    "Allowed /ask count: 4\n"
    "\n"
    "## Requirements\n"
    "\n"
    "- Repository with CRUD operations\n"
)


def test_engine_reuse_without_duplication():
    shared = ExamScorer().engine
    first = ExamScorer(engine=shared)
    second = ExamScorer(engine=shared)
    assert first.engine is second.engine is shared
    assert EXAM_RUBRIC.ref == "exam-default:v1"
    with pytest.raises(ExamDefinitionError):
        resolve_rubric("evaluate-default:v1")


def test_instrumented_rejected(tmp_path):
    services = make_context(tmp_path, make_project(tmp_path))
    action = ExamineAction(services, runner=OkRunner())
    with pytest.raises(InstrumentedNotSupportedError):
        action.finish(ExamFinishInput(confirmed=True, instrumented=True))


def test_functional_requirements_scored():
    scorer = ExamScorer()
    criteria = scorer.functional_criteria(make_definition(), make_evidence())
    assert criteria[0].requirement_id == "req://fr1"
    assert criteria[0].weight == pytest.approx(1.0)
    assert criteria[0].dimension == "functional_requirements"
    assert criteria[0].score is not None
    assert criteria[0].not_evaluated_reason is None
    assert criteria[0].evidence_refs


def test_no_source_modification(tmp_path):
    proj = make_project(tmp_path)
    statement = tmp_path / "exam.md"
    statement.write_text(STATEMENT, encoding="utf-8")
    services = make_context(tmp_path, proj)
    action = ExamineAction(services, runner=OkRunner())

    start = action.start(
        ExamStartInput(
            statement=str(statement),
            project_id="project://p1",
            confirmed=True,
        )
    )
    before = {p: p.read_bytes() for p in proj.rglob("*") if p.is_file()}
    result = action.finish(ExamFinishInput(confirmed=True))

    assert isinstance(result, ExamFinishResult)
    assert result.result.exam_attempt_id == start.attempt.exam_attempt_id
    after = {p: p.read_bytes() for p in proj.rglob("*") if p.is_file()}
    sources = {
        name: data
        for name, data in before.items()
        if name.suffix in {".kt", ".java", ".kts"} or name.name == "gradlew"
    }
    for name, data in sources.items():
        assert after[name] == data
    assert result.result.raw_score_50 is not None


class BuildFailRunner:
    """Fails only the compile step, exercising the build-failure policy."""

    def run(self, cmd, *, cwd=None, timeout=None):
        from ada_sensei.tools.subprocess import SubprocessResult

        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=1 if cmd[-1] == "assembleDebug" else 0,
            stdout="compilation error",
            stderr="",
            duration_s=0.1,
        )


def test_build_failure_marks_dependencies_not_evaluated(tmp_path):
    proj = make_project(tmp_path)
    statement = tmp_path / "exam.md"
    statement.write_text(STATEMENT, encoding="utf-8")
    services = make_context(tmp_path, proj)
    action = ExamineAction(services, runner=BuildFailRunner())
    action.start(
        ExamStartInput(
            statement=str(statement), project_id="project://p1", confirmed=True
        )
    )

    result = action.finish(ExamFinishInput(confirmed=True))

    assert any("build failed" in lim for lim in result.result.limitations)
    functional = [
        line
        for line in result.result.score_calculation.lines
        if line.dimension == "functional_requirements"
    ]
    assert functional
    assert all(
        line.score is None and line.not_evaluated_reason is not None
        for line in functional
    )
    assert isinstance(result, ExamFinishResult)


class InferenceClient(LLMClient):
    """Returns one architecture inference citing a real evidence id."""

    def __init__(self, evidence_ref: str, ungrounded_ref: str = "ev://missing"):
        self.evidence_ref = evidence_ref
        self.ungrounded_ref = ungrounded_ref

    def chat(self, messages, *, model=None, temperature=None):
        return "{}"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return json.dumps(
            {
                "feedback": "Solid structure overall.",
                "architecture": [
                    {
                        "claim": (
                            "inferred: the presentation layer delegates to a "
                            "view model"
                        ),
                        "evidence_refs": [self.evidence_ref],
                        "kind": "inferred",
                    },
                    {
                        "claim": "inferred: an offline cache exists",
                        "evidence_refs": [self.ungrounded_ref],
                        "kind": "inferred",
                    },
                ],
            }
        )


def test_inline_statement_starts_an_exam(tmp_path):
    """The CLI advertises an inline statement, so ``start`` must accept one.

    RQ-EXM-002 only requires a file-backed statement; this proves the advertised
    convenience works and that the resolved definition is persisted, so the
    finish path still scores against the statement that was issued.
    """
    proj = make_project(tmp_path)
    services = make_context(tmp_path, proj)
    action = ExamineAction(services, runner=OkRunner())

    started = action.start(
        ExamStartInput(
            statement=STATEMENT, project_id="project://p1", confirmed=True
        )
    )
    assert started.definition.title == "Midterm Android Exam"
    assert started.attempt.allowed_ask_count == 4

    finished = action.finish(ExamFinishInput(confirmed=True))
    assert finished.result.exam_id == started.attempt.exam_id
    assert finished.result.raw_score_50 is not None


def test_unresolvable_statement_reports_both_accepted_forms(tmp_path):
    """A single-line non-path statement is refused, and says what is accepted."""
    proj = make_project(tmp_path)
    services = make_context(tmp_path, proj)
    action = ExamineAction(services, runner=OkRunner())

    with pytest.raises(ExamDefinitionError) as excinfo:
        action.start(
            ExamStartInput(
                statement="midterm exam", project_id="project://p1", confirmed=True
            )
        )
    message = str(excinfo.value)
    assert "multi-line text" in message
    assert "PDF" in message


def test_inferred_architecture_claims_reach_the_report(tmp_path):
    """RQ-EXM-023/030: inferred statements reach the report, ungrounded ones do not.

    End-to-end through ``ExamineAction._assemble``: the architecture report the
    exam persists must carry the grounded inference and exclude the one citing an
    evidence id that was never collected. The deterministic score must be
    unchanged by the presence of inferences.
    """
    proj = make_project(tmp_path)
    statement = tmp_path / "exam.md"
    statement.write_text(STATEMENT, encoding="utf-8")

    def finish_with(client):
        services = make_context(tmp_path / f"run-{id(client)}", proj, client=client)
        action = ExamineAction(services, runner=OkRunner())
        action.start(
            ExamStartInput(
                statement=str(statement), project_id="project://p1", confirmed=True
            )
        )
        return action.finish(ExamFinishInput(confirmed=True)).result

    baseline = finish_with(None)

    # Discover a real evidence id from the collected evidence.
    grounded_ref = next(e.id for e in baseline.evidence if e.id)
    scored = finish_with(InferenceClient(grounded_ref))

    report = scored.architecture_report
    assert report is not None
    inferred = [c for c in report.claims if c.kind == "inferred"]
    assert len(inferred) == 1, "only the grounded inference survives"
    assert inferred[0].evidence_refs == [grounded_ref]
    assert "delegates" in inferred[0].claim
    # The claim citing an id that was never collected is reported, not kept.
    assert any("offline cache" in c.claim for c in scored.unsupported_claims)
    assert all("offline cache" not in c.claim for c in report.claims)

    # The baseline run had no client, so no inference could exist at all.
    assert not [c for c in baseline.architecture_report.claims if c.kind == "inferred"]
    # Inferences are narrative only: the score is identical.
    assert scored.raw_score_50 == baseline.raw_score_50
    assert scored.suggested_grade == baseline.suggested_grade