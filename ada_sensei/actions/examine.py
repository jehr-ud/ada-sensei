"""``/exam-init`` — the exam workflow adapter over the shared evaluation engine.

Mirrors ``EvaluateAction``: this module owns only exam orchestration (attempt
lifecycle, exam rubric, process metrics, architecture, report, persistence).
Evidence collection, requirement matching, and rubric mechanics come from
``ada_sensei.evaluation`` (ADR-022) and the exam supplies its own versioned
``RubricDefinition`` (ADR-023). ``EvaluateAction`` is never called: this is an
overlay, not a second implementation of project evaluation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..evaluation import (
    DEFAULT_MODEL,
    PROMPT_VERSION,
    EvaluationCriterionInput,
    EvaluationEngine,
    EvaluationExecutionPolicy,
    EvaluatorAgent,
    EvidenceContext,
    LLMArchitectureEvaluator,
    LLMRequirementEvaluator,
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
from ..exams.docs import REPORT_NAME, ExamDocsWriter
from ..exams.lifecycle import ExamLifecycle
from ..exams.models import (
    ASK_SUCCESS_EVENTS,
    AcceptanceCriterion,
    ExamAttempt,
    ExamDefinition,
    ExamDefinitionError,
    ExamEvent,
    ExamEventType,
    ExamResult,
    ExamStateError,
)
from ..exams.preparation import ExamPreparationService
from ..exams.report import ExamReportGenerator
from ..exams.rubric import EXAM_RUBRIC, resolve_rubric
from ..exams.scoring import ExamScorer
from ..exams.store import ExamStore
from ..locale.ui_strings import describe_blocker, get_ui_string
from ..toolchain.manager import ToolchainManager
from ..toolchain.models import ToolchainManifest, ToolchainPreparationResult
from ..tools.subprocess import SubprocessRunner
from ..urns import URN
from .base import ActionResult, ActionServices


class ExamConfirmationRequired(Exception):
    """Starting or finishing an exam needs an explicit confirmation."""


class ExamNotActiveError(Exception):
    """No exam attempt is active for this session."""


class InstrumentedNotSupportedError(Exception):
    """``connectedAndroidTest`` stays unimplemented (spec.md §Evaluation scope)."""


#: Evidence-collection stage -> localized progress UI key (RQ-EXM-048).
_PROGRESS_STAGE_KEYS: dict[str, str] = {
    "inspection": "exam_progress_inspecting",
    "build": "exam_progress_build",
    "unit_tests": "exam_progress_unit_tests",
    "lint": "exam_progress_lint",
    "detekt": "exam_progress_detekt",
}


def _or_not_evaluated(value: object) -> str:
    """Never print a bare ``None`` where a score belongs (RQ-EXM-014)."""
    return "not evaluated" if value is None else str(value)


def _empty_manifest() -> ToolchainManifest:
    return ToolchainManifest(
        policy_id="unknown",
        policy_version="unknown",
        resolution_policy="pinned-compatible-only",
        created_at=datetime.now(UTC),
    )


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
            rules += [f"- {limitation}" for limitation in self.definition.limitations]
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
        report = result.evaluation_report
        max_raw = calculation.max_raw_score if calculation else 50
        max_grade = calculation.max_grade if calculation else 5.0
        raw = _or_not_evaluated(
            report.overall_score_50 if report is not None else result.raw_score_50
        )
        grade = _or_not_evaluated(
            report.suggested_grade if report is not None else result.suggested_grade
        )
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
        if report is not None:
            parts.append(f"Evaluation status: {report.overall_status.value}")
            if report.coverage_summary is not None:
                parts.append(
                    "Coverage: "
                    f"{report.coverage_summary.evaluated_criteria}/"
                    f"{report.coverage_summary.total_criteria} criteria, "
                    f"excluded weight {report.coverage_summary.excluded_weight:g}"
                )
        for dimension, score in result.dimension_scores.items():
            parts.append(f"- {dimension}: {_or_not_evaluated(score)}")
        if result.not_evaluated:
            parts.append("Not evaluated: " + ", ".join(result.not_evaluated))
        if result.strengths:
            parts.append("Strengths:\n" + "\n".join(f"- {s}" for s in result.strengths))
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
        progress: Callable[[str], None] | None = None,
        toolchain: Any | None = None,
    ) -> None:
        self.services = services
        self.engine = engine or EvaluationEngine()
        self._runner = runner
        self.toolchain = toolchain if toolchain is not None else ToolchainManager()
        #: Optional localized progress sink, driven by the TUI (RQ-EXM-048).
        self._progress_callback = progress
        self.store = ExamStore(services.data_dir)
        self.scorer = ExamScorer()
        self.loader = ExamDefinitionLoader()
        self.evaluator = EvaluatorAgent()
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

    def _active_locale(self, student_id: str) -> str:
        """Active locale snapshot for the attempt (spec 0010, RQ-LNG-013)."""
        from ..locale.models import FALLBACK_LOCALE
        from ..locale.service import LocaleService
        from ..locale.store import LocalePreferenceStore

        try:
            svc = LocaleService(LocalePreferenceStore(self.services.data_dir))
            return svc.get_or_prompt_locale(student_id) or FALLBACK_LOCALE
        except Exception:  # noqa: BLE001 - snapshot must never break start
            return FALLBACK_LOCALE

    @property
    def docs(self) -> ExamDocsWriter:
        return self._resolve_docs()

    def _progress(self, key: str, locale: str) -> None:
        """Emit one localized progress message, if a sink is attached."""
        if self._progress_callback is None:
            return
        self._progress_callback(get_ui_string(key, locale))

    # -- start ------------------------------------------------------------

    def start(self, inp: ExamStartInput) -> ExamStartResult:
        """RQ-EXM-003: confirm, resolve identities, create the attempt and docs."""
        if not inp.confirmed:
            raise ExamConfirmationRequired(
                "starting an exam requires explicit confirmation"
            )
        # The application boundary repeats the preparation check.  The TUI is
        # only a presenter and cannot be trusted to keep a preflight fresh.
        configured_definition = self.services.context.exam_definition_path
        statement_text = inp.statement.strip()
        definition_source = None
        is_inline = statement_text.startswith("{")
        is_path = False
        if not is_inline and statement_text:
            try:
                is_path = Path(statement_text).expanduser().is_file()
            except (OSError, ValueError):
                is_path = False
        if is_inline or is_path:
            definition_source = statement_text
        locale = (
            self._active_locale(self.services.context.student_id)
            if self.services.context.student_id
            else None
        )
        status = ExamPreparationService(
            self.services, toolchain=self.toolchain, progress=self._progress_callback
        ).validate(
            require_exam_definition=bool(configured_definition or definition_source)
            or not statement_text,
            definition_source=definition_source,
            locale=locale,
        )
        if not status.ready_to_start:
            reasons = "; ".join(
                describe_blocker(
                    code,
                    locale,
                    detail=(
                        status.toolchain_blockers[0]
                        if code == "toolchain_not_ready" and status.toolchain_blockers
                        else ""
                    ),
                )
                for code in status.blockers
            )
            raise ExamStateError(
                "exam preparation incomplete: " + (reasons or "unknown reason")
            )
        if configured_definition:
            if (
                inp.statement
                and not inp.statement.strip().startswith("{")
                and Path(inp.statement).expanduser().resolve()
                != Path(configured_definition).expanduser().resolve()
            ):
                raise ExamDefinitionError(
                    "exam statement differs from configured exam definition"
                )
            statement = configured_definition
        else:
            statement = inp.statement
        definition = self._resolve_definition(statement)
        student_id = self._require_student(inp.student_id)
        project_id = self._require_project(inp.project_id)
        preparation = status.toolchain_preparation
        self._progress("exam_start_progress_ready", locale)
        attempt = self.lifecycle.start(
            definition,
            student_id=student_id,
            project_id=project_id,
            project_root=self._project_path(),
            exercise_id=inp.exercise_id or self.services.context.current_exercise_id,
            attempt_id=self.services.context.attempt_id or None,
            locale=self._active_locale(student_id),
            toolchain_manifest=preparation.manifest if preparation else None,
            toolchain_evidence=list(preparation.executions) if preparation else [],
        )
        # The session now knows which attempt is live, so `/ask` is attributed to
        # it without the student restating the id (RQ-EXM-001).
        self.services.context.exam_attempt_id = attempt.exam_attempt_id
        self._attach_bridge(attempt)
        self.services.context.persist()
        return ExamStartResult(attempt=attempt, definition=definition)

    def _resolve_definition(self, statement: str) -> ExamDefinition:
        """Accept a validated JSON file or an inline JSON definition.

        Markdown and PDF are no longer authoritative requirement sources. Inline
        JSON is accepted for the advertised convenience; the resolved definition
        is persisted at start time so the finish path never re-reads the original
        (see ``ExamStore.save_definition``).
        """
        text = statement.strip()
        if not text:
            raise ExamDefinitionError("exam statement is empty")
        if text.startswith("{"):
            return self.loader.load_text(text, exam_id=None)
        path = Path(text).expanduser()
        if path.is_file():
            return self.loader.load(path, exam_id=None)
        raise ExamDefinitionError(
            f"exam statement not found: {path}. Pass a .json file path or an "
            "inline JSON exam definition."
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
        from ..locale.models import FALLBACK_LOCALE

        locale = attempt.locale or FALLBACK_LOCALE
        definition = self._definition_for(attempt)
        self.lifecycle.request_finish(attempt, confirmed=True)
        self._log(attempt, ExamEventType.evaluation_started)

        def on_stage(stage: str) -> None:
            key = _PROGRESS_STAGE_KEYS.get(stage)
            if key:
                self._progress(key, locale)

        evidence = self.engine.collect_evidence(
            ProjectContext.from_path(self._project_path()),
            None,
            self._policy(),
            runner=self._runner,
            progress=on_stage,
        )
        self.lifecycle.finish(attempt)
        self._detach_bridge()

        self._progress("exam_progress_interpreting", locale)
        result = self._assemble(attempt, definition, evidence)
        self._progress("exam_progress_report", locale)
        # RQ-EXM-024: the report lives inside the examined project, next to the
        # other generated exam documentation, never in ADA Sensei's data dir.
        docs = self.docs.docs_for(definition.exam_id)
        report_target = docs.ensure() / REPORT_NAME
        path, report_id = self.reports.generate(result, definition, path=report_target)
        result.report_id = report_id
        result.report_path = str(path)
        self.docs.write_finish_docs(result, definition, docs=docs)
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
        """Build one official report from LLM decisions and deterministic evidence.

        The LLM only returns statuses tied to real evidence ids. Every number,
        weight and denominator is computed here by ``ExamScorer`` and then
        projected once into ``EvaluationReport`` for the CLI and the PDF.
        """
        rubric = self._require_exam_rubric(attempt.rubric_ref)
        scorer = ExamScorer(rubric)
        if evidence.project_path is None:
            evidence.project_path = str(self._project_path())
        build_failed = self.engine.build_failed(evidence)
        analyzer = ArchitectureAnalyzer(self._project_path())
        architecture = analyzer.analyze(evidence, definition)
        documentation = [
            str(path.relative_to(self._project_path()))
            for path in definition.documentation_paths(self._project_path())
        ]
        requirement_inputs = self._criterion_inputs(definition)
        model = self.services.config.llm.model or DEFAULT_MODEL
        prompt_version = PROMPT_VERSION
        requirement_batch = LLMRequirementEvaluator(
            self.services.client, model=model, prompt_version=prompt_version
        ).evaluate(requirement_inputs, evidence)
        architecture_batch = LLMArchitectureEvaluator(
            self.services.client, model=model, prompt_version=prompt_version
        ).evaluate(evidence)
        requirement_decisions = {
            item.criterion_id: item for item in requirement_batch.decisions
        }
        architecture_decisions = {
            item.criterion_id: item for item in architecture_batch.decisions
        }
        calculation = scorer.score(
            definition,
            evidence,
            attempt=attempt,
            architecture=architecture,
            build_failed=build_failed,
            extra_limitations=list(definition.limitations),
            requirement_decisions=requirement_decisions,
            architecture_decisions=architecture_decisions,
        )
        metrics = scorer.process_criteria(attempt)
        agent = ExamInterpretationAgent(
            self.services.client,
            model=model,
            temperature=self.services.config.llm.temperature,
            max_attempts=self.services.config.llm.max_attempts,
        )
        interpretation = self._interpret(
            agent, definition, evidence, metrics, calculation, documentation
        )
        architecture = analyzer.analyze(
            evidence,
            definition,
            inferred_claims=interpretation.architecture_claims,
        )
        result = self._result(
            attempt,
            definition,
            evidence,
            calculation,
            metrics,
            architecture,
            interpretation,
            documentation,
            build_failed,
            scorer=scorer,
        )
        official_report = self.evaluator.build_report(
            result=result,
            definition=definition,
            evidence=evidence,
            build_failed=build_failed,
            toolchain_preparation=self._toolchain_preparation(attempt),
            requirement_decisions=requirement_decisions,
            architecture_decisions=architecture_decisions,
            llm_runs=[requirement_batch.run, architecture_batch.run],
            rubric_definition=rubric,
        )
        result.evaluation_report = official_report
        result.strengths = official_report.strengths or interpretation.strengths()
        result.recommendations = [
            item.text for item in official_report.priority_actions
        ] or interpretation.recommendations()
        result.feedback = "\n".join(result.strengths + result.recommendations)
        result.toolchain_manifest = attempt.toolchain_manifest
        result.toolchain_evidence = list(attempt.toolchain_evidence)
        return result

    @staticmethod
    def _criterion_inputs(
        definition: ExamDefinition,
    ) -> list[EvaluationCriterionInput]:
        inputs: list[EvaluationCriterionInput] = []
        for requirement in definition.requirements:
            acceptance = list(requirement.acceptance_criteria)
            if not acceptance:
                acceptance = [
                    AcceptanceCriterion(
                        id=requirement.requirement_id,
                        description=requirement.description,
                        verification=["source_inspection"],
                    )
                ]
            for item in acceptance:
                inputs.append(
                    EvaluationCriterionInput(
                        criterion_id=item.id,
                        description=item.description,
                        requirement_id=requirement.requirement_id,
                        dimension=requirement.dimension,
                    )
                )
        return inputs

    @staticmethod
    def _toolchain_preparation(attempt: ExamAttempt) -> ToolchainPreparationResult:
        executions = list(attempt.toolchain_evidence)
        ready = bool(
            attempt.toolchain_manifest is not None
            and executions
            and all(item.health_check.status.value == "PASS" for item in executions)
        )
        return ToolchainPreparationResult(
            ready=ready,
            manifest=attempt.toolchain_manifest or _empty_manifest(),
            executions=executions,
            blockers=[] if ready else ["toolchain evidence is unavailable"],
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
                    strengths=[],
                    weaknesses=[],
                    recommendations=[],
                    findings=[],
                    feedback=(
                        "The qualitative interpretation could not be generated; "
                        "the deterministic score below is unaffected."
                    ),
                    next_learning_activity="",
                    limitations=[reason],
                    architecture=[],
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
        scorer: ExamScorer | None = None,
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
            criteria=list(calculation.criteria),
            dimension_scores={line.dimension: line.score for line in calculation.lines},
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
            # Snapshot locale wins over the current profile locale so the
            # report stays consistent when the language changed mid-exam
            # (spec 0010, RQ-LNG-013).
            locale=attempt.locale or self._active_locale(attempt.student_id),
            supersedes_report_id=attempt.administrative_metadata.get(
                "supersedes_report_id"
            ),
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
            raise ExamStateError(f"exam attempt {exam_attempt_id} is already completed")
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
                f"exam attempts must be scored with {EXAM_RUBRIC.id}, not {rubric.id}"
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
