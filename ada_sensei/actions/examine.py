"""``/exam-init`` — the exam workflow adapter over the shared evaluation engine.

Mirrors ``EvaluateAction``: this module owns only exam orchestration (attempt
lifecycle, exam rubric, process metrics, architecture, report, persistence).
Evidence collection, requirement matching, and rubric mechanics come from
``ada_sensei.evaluation`` (ADR-022) and the exam supplies its own versioned
``RubricDefinition`` (ADR-023). ``EvaluateAction`` is never called: this is an
overlay, not a second implementation of project evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..evaluation import (
    EvaluationEngine,
    EvaluationExecutionPolicy,
    EvidenceContext,
    ProjectContext,
    RubricDefinition,
    unsupported_claim_summary,
)
from ..exams.agent import (
    ExamInterpretation,
    ExamInterpretationAgent,
    GroundedExamInterpretation,
)
from ..exams.architecture import ArchitectureAnalyzer
from ..exams.definition import ExamDefinitionLoader
from ..exams.docs import ExamDocsWriter
from ..exams.lifecycle import ExamLifecycle
from ..exams.models import (
    ASK_SUCCESS_EVENTS,
    ExamAttempt,
    ExamDefinition,
    ExamDefinitionError,
    ExamEvent,
    ExamEventType,
    ExamResult,
    ExamStateError,
)
from ..exams.report import ExamReportGenerator
from ..exams.rubric import EXAM_RUBRIC, resolve_rubric
from ..exams.scoring import ExamScorer
from ..exams.store import ExamStore
from ..tools.subprocess import SubprocessRunner
from ..urns import URN
from .base import ActionResult, ActionServices


class ExamConfirmationRequired(Exception):
    """Starting or finishing an exam needs an explicit confirmation."""


class ExamNotActiveError(Exception):
    """No exam attempt is active for this session."""


class InstrumentedNotSupportedError(Exception):
    """``connectedAndroidTest`` stays unimplemented (spec.md §Evaluation scope)."""


def _or_not_evaluated(value: object) -> str:
    """Never print a bare ``None`` where a score belongs (RQ-EXM-014)."""
    return "not evaluated" if value is None else str(value)


@dataclass
class ExamStartInput:
    statement: str
    student_id: str | None = None
    project_id: str | None = None
    exercise_id: str | None = None
    confirmed: bool = False


@dataclass
class ExamFinishInput:
    confirmed: bool = False
    instrumented: bool = False


@dataclass
class ExamStartResult(ActionResult):
    attempt: ExamAttempt
    definition: ExamDefinition

    def present(self) -> str:
        rules = [
            f"Exam started: {self.definition.title or self.definition.exam_id}",
            f"Exam attempt: {self.attempt.exam_attempt_id}",
            f"Student: {self.attempt.student_id}",
            f"Project: {self.attempt.project_id}",
        ]
        if self.attempt.allowed_duration_seconds is not None:
            minutes = self.attempt.allowed_duration_seconds / 60
            rules.append(f"Allowed duration: {minutes:g} minutes")
        else:
            rules.append("Allowed duration: not defined")
        if self.attempt.allowed_ask_count is not None:
            rules.append(f"Allowed /ask usage: {self.attempt.allowed_ask_count}")
        else:
            rules.append("Allowed /ask usage: not defined")
        if self.definition.limitations:
            rules.append("Statement limitations:")
            rules += [
                f"- {limitation}" for limitation in self.definition.limitations
            ]
        if self.attempt.docs_dir:
            rules.append(f"Exam context written to: {self.attempt.docs_dir}")
        rules.append("Finish with 'Finish Exam' when you are done.")
        return "\n".join(rules)


@dataclass
class ExamFinishResult(ActionResult):
    result: ExamResult
    report_path: str

    def present(self) -> str:
        result = self.result
        calculation = result.score_calculation
        max_raw = calculation.max_raw_score if calculation else 50
        max_grade = calculation.max_grade if calculation else 5.0
        raw = _or_not_evaluated(result.raw_score_50)
        grade = _or_not_evaluated(result.suggested_grade)
        parts = [f"Exam finished: {result.exam_title or result.exam_id}"]
        parts.append(f"Exam attempt: {result.exam_attempt_id}")
        parts.append(f"Student: {result.student_id}")
        parts.append(f"Project: {result.project_id}")
        if result.duration_seconds is not None:
            parts.append(f"Duration: {result.duration_seconds}s")
        allowed = (
            f" of {result.allowed_ask_count}"
            if result.allowed_ask_count is not None
            else ""
        )
        parts.append(f"/ask usage: {result.ask_count}{allowed}")
        parts.append(f"Raw score: {raw}/{max_raw}")
        parts.append(f"Suggested grade: {grade}/{max_grade}")
        for dimension, score in result.dimension_scores.items():
            parts.append(f"- {dimension}: {_or_not_evaluated(score)}")
        if result.not_evaluated:
            parts.append("Not evaluated: " + ", ".join(result.not_evaluated))
        if result.strengths:
            parts.append(
                "Strengths:\n" + "\n".join(f"- {s}" for s in result.strengths)
            )
        if result.weaknesses:
            parts.append(
                "Weaknesses:\n" + "\n".join(f"- {w}" for w in result.weaknesses)
            )
        if result.recommendations:
            parts.append(
                "Recommendations:\n"
                + "\n".join(f"- {r}" for r in result.recommendations)
            )
        if result.unsupported_claims:
            parts.append(unsupported_claim_summary(result.unsupported_claims))
        if result.limitations:
            parts.append(
                "Limitations:\n" + "\n".join(f"- {lim}" for lim in result.limitations)
            )
        parts.append(result.grade_disclosure)
        parts.append(f"Report: {self.report_path}")
        return "\n\n".join(parts)


class ExamineAction:
    """Starts and finishes one exam, persisting the result and its report."""

    def __init__(
        self,
        services: ActionServices,
        runner: SubprocessRunner | None = None,
        engine: EvaluationEngine | None = None,
    ) -> None:
        self.services = services
        self.engine = engine or EvaluationEngine()
        self._runner = runner
        self.store = ExamStore(services.data_dir)
        self.scorer = ExamScorer()
        self.loader = ExamDefinitionLoader()
        # The project path is resolved lazily: constructing the action must not
        # require a configured project, only running it does.
        self._docs: ExamDocsWriter | None = None
        self.lifecycle = ExamLifecycle(
            self.store, services.event_bus, self._resolve_docs
        )
        self.reports = ExamReportGenerator(
            services.config.resolved_data_dir / "reports"
        )

    def _resolve_docs(self) -> ExamDocsWriter:
        if self._docs is None:
            self._docs = ExamDocsWriter(self._project_path())
        return self._docs

    @property
    def docs(self) -> ExamDocsWriter:
        return self._resolve_docs()

    # -- start ------------------------------------------------------------

    def start(self, inp: ExamStartInput) -> ExamStartResult:
        """RQ-EXM-003: confirm, resolve identities, create the attempt and docs."""
        if not inp.confirmed:
            raise ExamConfirmationRequired(
                "starting an exam requires explicit confirmation"
            )
        definition = self._resolve_definition(inp.statement)
        student_id = self._require_student(inp.student_id)
        project_id = self._require_project(inp.project_id)
        attempt = self.lifecycle.start(
            definition,
            student_id=student_id,
            project_id=project_id,
            project_root=self._project_path(),
            exercise_id=inp.exercise_id or self.services.context.current_exercise_id,
            attempt_id=self.services.context.attempt_id or None,
        )
        # The session now knows which attempt is live, so `/ask` is attributed to
        # it without the student restating the id (RQ-EXM-001).
        self.services.context.exam_attempt_id = attempt.exam_attempt_id
        self._attach_bridge(attempt)
        self.services.context.persist()
        return ExamStartResult(attempt=attempt, definition=definition)

    def _resolve_definition(self, statement: str) -> ExamDefinition:
        """Accept an instructor file path or a statement supplied inline.

        RQ-EXM-002 requires a file-backed Markdown/structured/PDF statement. The
        CLI also advertises inline text, so a multi-line statement is accepted
        directly instead of failing the "statement not found" path. Either way
        the resolved definition is persisted at start time, so the finish path
        never re-reads the original (see ``ExamStore.save_definition``).
        """
        text = statement.strip()
        if not text:
            raise ExamDefinitionError("exam statement is empty")
        path = Path(text).expanduser()
        if path.is_file():
            return self.loader.load(path, exam_id=None)
        if "\n" in text or text.startswith(("{", "[")):
            return self.loader.load_text(text, exam_id=None)
        raise ExamDefinitionError(
            f"exam statement not found: {path}. Pass a Markdown, structured or "
            "PDF file path, or pass the statement as multi-line text."
        )

    # -- finish -----------------------------------------------------------

    def finish(self, inp: ExamFinishInput | None = None) -> ExamFinishResult:
        """RQ-EXM-004/007: confirm, stop the timer, score, report, persist."""
        inp = inp or ExamFinishInput()
        if inp.instrumented:
            raise InstrumentedNotSupportedError(
                "--instrumented (connectedAndroidTest) is reserved for a future "
                "option and is not supported now"
            )
        attempt = self._require_active_attempt()
        if not inp.confirmed:
            raise ExamConfirmationRequired(
                "finishing an exam requires explicit confirmation"
            )
        definition = self._definition_for(attempt)
        self.lifecycle.request_finish(attempt, confirmed=True)
        self._log(attempt, ExamEventType.evaluation_started)

        evidence = self.engine.collect_evidence(
            ProjectContext.from_path(self._project_path()),
            None,
            self._policy(),
            runner=self._runner,
        )
        self.lifecycle.finish(attempt)
        self._detach_bridge()

        result = self._assemble(attempt, definition, evidence)
        path, report_id = self.reports.generate(result, definition)
        result.report_id = report_id
        result.report_path = str(path)
        self.docs.write_finish_docs(result, definition)
        self._log(attempt, ExamEventType.evaluation_completed)
        self._persist(result, attempt)
        self.services.context.clear_exam()
        self.services.context.persist()
        return ExamFinishResult(result=result, report_path=str(path))

    # -- assembly ---------------------------------------------------------

    def _assemble(
        self,
        attempt: ExamAttempt,
        definition: ExamDefinition,
        evidence: EvidenceContext,
    ) -> ExamResult:
        """Deterministic score plus grounded qualitative interpretation.

        Ordering matters: architecture is analysed from observed evidence, the
        score is computed, and only then does the model interpret that score. The
        model never supplies a number (spec.md §Structured LLM output).
        """
        self._require_exam_rubric(attempt.rubric_ref)
        build_failed = self.engine.build_failed(evidence)
        analyzer = ArchitectureAnalyzer(self._project_path())
        report = analyzer.analyze(evidence, definition)
        documentation = [
            str(path.relative_to(self._project_path()))
            for path in definition.documentation_paths(self._project_path())
        ]
        calculation = self.scorer.score(
            definition,
            evidence,
            attempt=attempt,
            architecture=report,
            build_failed=build_failed,
            extra_limitations=list(definition.limitations),
        )
        metrics = self.scorer.process_criteria(attempt)
        agent = ExamInterpretationAgent(
            self.services.client,
            model=self.services.config.llm.model,
            temperature=self.services.config.llm.temperature,
            max_attempts=self.services.config.llm.max_attempts,
        )
        interpretation = self._interpret(
            agent, definition, evidence, metrics, calculation, documentation
        )
        # Ground the model's architecture inferences into the report now that they
        # exist. This cannot move the score: ``architecture_score`` reads observed
        # claims only, and those are already fixed above (RQ-EXM-014, RQ-EXM-030).
        # Re-analysing here is what lets inferred claims reach the narrative and
        # the PDF report, which RQ-EXM-023/030 require, while the model still
        # never influences a number.
        report = analyzer.analyze(
            evidence,
            definition,
            inferred_claims=interpretation.architecture_claims,
        )
        return self._result(
            attempt,
            definition,
            evidence,
            calculation,
            metrics,
            report,
            interpretation,
            documentation,
            build_failed,
        )

    def _interpret(
        self,
        agent,
        definition: ExamDefinition,
        evidence: EvidenceContext,
        metrics,
        calculation,
        documentation: list[str],
    ):
        """A failed interpretation degrades the narrative, never the score."""
        try:
            return agent.interpret(
                definition,
                evidence,
                metrics,
                {line.dimension: line.score for line in calculation.lines},
                documentation,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
            reason = f"exam interpretation unavailable: {type(exc).__name__}: {exc}"
            return GroundedExamInterpretation(
                interpretation=ExamInterpretation(
                    feedback=(
                        "The qualitative interpretation could not be generated; "
                        "the deterministic score below is unaffected."
                    ),
                    limitations=[reason],
                )
            )

    def _result(
        self,
        attempt: ExamAttempt,
        definition: ExamDefinition,
        evidence: EvidenceContext,
        calculation,
        metrics,
        report,
        interpretation,
        documentation: list[str],
        build_failed: bool,
    ) -> ExamResult:
        limitations: list[str] = [
            *evidence.limitations,
            *interpretation.interpretation.limitations,
        ]
        for line in calculation.lines:
            if line.not_evaluated_reason is not None:
                limitations.append(
                    f"{line.dimension}: not evaluated "
                    f"({line.not_evaluated_reason.value})"
                )
        if build_failed:
            limitations.append(
                "build failed; compilation-dependent dimensions are not evaluated"
            )
        if not documentation:
            limitations.append(
                "no student documentation matched the exam documentation rules"
            )
        unsupported = list(interpretation.unsupported_claims)
        for claim in report.unsupported_claims:
            limitations.append(
                f"unsupported architecture claim excluded: {claim.claim} "
                f"({claim.reason})"
            )
        return ExamResult(
            id=URN.make("result"),
            attempt_id=attempt.attempt_id,
            exercise_id=attempt.exercise_id,
            student_id=attempt.student_id,
            project_id=attempt.project_id,
            exam_id=attempt.exam_id,
            exam_attempt_id=attempt.exam_attempt_id,
            exam_title=definition.title,
            rubric_id=calculation.rubric_id,
            rubric_version=calculation.rubric_version,
            overall_score=calculation.percentage,
            criteria=self.scorer.functional_criteria(definition, evidence),
            dimension_scores={
                line.dimension: line.score for line in calculation.lines
            },
            evidence=list(evidence.evidence),
            strengths=interpretation.strengths(),
            weaknesses=interpretation.weaknesses(),
            feedback=interpretation.interpretation.feedback,
            recommendations=interpretation.recommendations(),
            next_learning_activity=interpretation.interpretation.next_learning_activity,
            limitations=limitations,
            unsupported_claims=unsupported,
            not_evaluated=[
                line.dimension
                for line in calculation.lines
                if line.not_evaluated_reason is not None
            ],
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
            ask_count=attempt.ask_count,
            allowed_ask_count=attempt.allowed_ask_count,
            duration_seconds=attempt.duration_seconds,
            allowed_duration_seconds=attempt.allowed_duration_seconds,
            overtime_seconds=attempt.overtime_seconds,
            process_metrics=metrics,
            architecture_report=report,
            score_calculation=calculation,
            raw_score_50=calculation.raw_score_50,
            suggested_grade=calculation.suggested_grade,
        )

    # -- resolution -------------------------------------------------------

    def _project_path(self) -> Path:
        project_path = self.services.config.project.path
        if project_path in (None, "", "."):
            raise LookupError("no active project configured")
        return Path(str(project_path)).expanduser()

    def _require_student(self, explicit: str | None) -> str:
        """RQ-EXM-001: identity comes from the flag or the session, never the
        statement text."""
        student_id = explicit or self.services.context.student_id
        if not student_id:
            raise LookupError(
                "no student selected; pass --student <student_id> or set the "
                "session student first"
            )
        return student_id

    def _require_project(self, explicit: str | None) -> str:
        project_id = explicit or self.services.context.project_id
        if not project_id:
            raise LookupError(
                "no project selected; pass --project <project_id> or set the "
                "session project first"
            )
        return project_id

    def _require_active_attempt(self) -> ExamAttempt:
        exam_attempt_id = self.services.context.exam_attempt_id
        if not exam_attempt_id:
            raise ExamNotActiveError(
                "no exam is active in this session; start one with 'exam-init'"
            )
        attempt = self.store.get(exam_attempt_id)
        if attempt is None:
            raise ExamNotActiveError(f"unknown exam attempt: {exam_attempt_id}")
        if attempt.is_completed:
            raise ExamStateError(
                f"exam attempt {exam_attempt_id} is already completed"
            )
        # RQ-EXM-031: the ask count is recounted from the attempt log, which is
        # the authoritative record, rather than read from a stored total.
        attempt.ask_count = sum(
            1
            for event in self.store.list_events(exam_attempt_id)
            if event.type in ASK_SUCCESS_EVENTS
        )
        return attempt

    @staticmethod
    def _require_exam_rubric(rubric_ref: str) -> RubricDefinition:
        """ADR-023: the exam uses its own rubric, never ``evaluate-default:v1``.

        Resolving here turns a tampered attempt record into an explicit error
        instead of silently scoring the exam with the exercise rubric.
        """
        rubric = resolve_rubric(rubric_ref)
        if rubric.id != EXAM_RUBRIC.id:
            raise ExamStateError(
                f"exam attempts must be scored with {EXAM_RUBRIC.id}, "
                f"not {rubric.id}"
            )
        return rubric

    def _definition_for(self, attempt: ExamAttempt) -> ExamDefinition:
        """The statement persisted at start time, never re-read from disk."""
        definition = self.store.get_definition(attempt.exam_id)
        if definition is None:
            raise ExamStateError(
                f"exam definition for {attempt.exam_id} is missing; the attempt "
                "cannot be scored against an unknown statement"
            )
        return definition

    def _policy(self) -> EvaluationExecutionPolicy:
        """RQ-EXM-010: the default scope, reusing the 006 confirmation policy."""
        return EvaluationExecutionPolicy(
            gradle_confirmed=True,
            run_build=True,
            run_unit_tests=True,
            run_lint=True,
            run_detekt=True,
            run_instrumented=False,
            timeout_seconds=self.services.config.tools.timeout_seconds,
        )

    # -- events and persistence -------------------------------------------

    def _attach_bridge(self, attempt: ExamAttempt) -> None:
        """Reuse the lifecycle's single ask bridge.

        ``ExamLifecycle.start`` already subscribed one; subscribing another here
        would record every ``/ask`` twice and inflate the exam counter
        (RQ-EXM-005, RQ-EXM-031).
        """
        if not self.lifecycle.bridge_attached:
            self.lifecycle.attach_bridge(attempt)

    def _detach_bridge(self) -> None:
        self.lifecycle.detach_bridge()

    def _log(self, attempt: ExamAttempt, event_type: str) -> None:
        event = ExamEvent(
            exam_attempt_id=attempt.exam_attempt_id,
            type=ExamEventType(event_type),
        )
        self.store.append(event)
        attempt.event_ids.append(event.event_id)

    def _persist(self, result: ExamResult, attempt: ExamAttempt) -> None:
        """RQ-EXM-026/027: failures are explicit, never swallowed."""
        try:
            self.services.results.save(result)
        except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
            result.limitations.append(
                f"exam result {result.id} was NOT persisted: {exc}"
            )
        if attempt.attempt_id:
            try:
                self.services.attempts.mark_completed(attempt.attempt_id)
            except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
                result.limitations.append(
                    f"attempt {attempt.attempt_id} was NOT marked completed: {exc}"
                )
        try:
            self.services.history.append_exam_result(result.student_id, result)
        except Exception as exc:  # noqa: BLE001 - surfaced as a limitation
            result.limitations.append(
                f"exam outcome NOT appended to history for {result.student_id}: {exc}"
            )


__all__ = [
    "ExamineAction",
    "ExamConfirmationRequired",
    "ExamFinishInput",
    "ExamFinishResult",
    "ExamNotActiveError",
    "ExamStartInput",
    "ExamStartResult",
    "InstrumentedNotSupportedError",
]
