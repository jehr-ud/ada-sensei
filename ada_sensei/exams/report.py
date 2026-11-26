"""Official exam PDF renderer (006-evaluate v2, 007-examine v2).

The PDF is a projection of ``ExamResult.evaluation_report``. It never scores,
re-weighs, re-groups or re-interprets anything; every number and every cited
evidence identifier printed here is read from the one official report object.
"""

from __future__ import annotations

from pathlib import Path

from ..evaluation.models import (
    NON_EVALUABLE_STATUSES,
    CriterionResult,
    EvaluationReport,
    EvidenceReference,
)
from ..urns import URN
from .models import SUGGESTED_GRADE_LABEL, ExamDefinition, ExamResult
from .pdf import SimplePdfWriter

SECTIONS = (
    "1. Identification",
    "2. Global summary and coverage",
    "3. Dimension results",
    "4. Functional requirements and criteria",
    "5. Architecture D4 split",
    "6. Tests and code quality",
    "7. Limitations",
    "8. Priority actions",
)

MAX_ACTIONS = 5
MAX_FINDING_GROUPS = 8
MAX_TOOL_RUNS = 8
MAX_REQUIREMENTS = 20
MAX_CRITERIA_PER_REQUIREMENT = 8
MAX_EVIDENCE_PER_CRITERION = 2

class ExamReportGenerator:
    """Renders one ``EvaluationReport`` into a compact, auditable PDF."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def default_path(self, result: ExamResult) -> Path:
        return self.output_dir / "exams" / f"{_slug(result.exam_attempt_id)}.pdf"

    def generate(
        self,
        result: ExamResult,
        definition: ExamDefinition | None = None,
        path: str | Path | None = None,
    ) -> tuple[Path, str]:
        """Write the PDF and return ``(path, report_id)``."""
        target = Path(path) if path is not None else self.default_path(result)
        target.parent.mkdir(parents=True, exist_ok=True)
        report_id = result.report_id or URN.make("exam_report")
        target.write_bytes(self._render(result, definition, report_id))
        return target, report_id

    def render_text(self, result: ExamResult) -> str:
        """Plain-text twin of the PDF, used by assertions and previews."""
        lines: list[str] = []
        for heading, body in self._sections(result):
            lines += [f"## {heading}", "", body, ""]
        lines += [result.grade_disclosure, f"Suggested grade: {SUGGESTED_GRADE_LABEL}."]
        return "\n".join(lines).strip() + "\n"

    def _render(
        self,
        result: ExamResult,
        definition: ExamDefinition | None,
        report_id: str,
    ) -> bytes:
        writer = SimplePdfWriter(body_size=9.5, leading=12.0, margin=48.0)
        for heading, body in self._sections(result):
            writer.heading(heading, 2)
            for kind, text in _blocks(body):
                if kind == "p":
                    writer.paragraph(text)
                else:
                    writer.bullet(text)
        report = result.evaluation_report
        writer.footer(
            left=f"Attempt {result.exam_attempt_id}",
            right=f"Report {report.report_id if report else report_id}",
        )
        return writer.build()

    def _sections(self, result: ExamResult) -> list[tuple[str, str]]:
        report = result.evaluation_report
        if report is None:
            return _legacy_sections(result)
        pairs = [
            ("1. Identification", self._identification(report, result)),
            ("2. Global summary and coverage", self._summary(report)),
            ("3. Dimension results", self._dimensions(report)),
            ("4. Functional requirements and criteria", self._functional(report)),
            ("5. Architecture D4 split", self._architecture(report)),
            ("6. Tests and code quality", self._quality(report)),
            ("7. Limitations", self._limitations(report)),
            ("8. Priority actions", self._actions(report)),
        ]
        return [(heading, body) for heading, body in pairs if body]

    @staticmethod
    def _identification(report: EvaluationReport, result: ExamResult) -> str:
        lines = [
            f"Report: {report.report_id}",
            f"Student: {report.student_id}",
            f"Project: {report.project_id}",
            f"Exam: {report.exam_id}",
            f"Exam attempt: {report.attempt_id}",
            f"Generated: {_timestamp(report.generated_at)}",
            f"Locale: {report.locale}",
            f"Rubric: {report.rubric_id}:{report.rubric_version}",
            f"Status: {report.overall_status.value}",
        ]
        if report.llm_runs:
            run = report.llm_runs[0]
            lines.append(
                f"LLM: {run.provider}/{run.model_id} prompt {run.prompt_id}:"
                f"{run.prompt_version} temperature {run.temperature:g} "
                f"attempts {run.attempts}"
            )
        language = _language_line(result.locale)
        if language:
            lines.append(language)
        lines.append(result.grade_disclosure)
        return "\n".join(lines)

    @staticmethod
    def _summary(report: EvaluationReport) -> str:
        lines = [
            f"Raw score: {_or_not_evaluated(report.overall_score_50)} of 50",
            f"Score (0-5): {_or_not_evaluated(report.overall_score_5)}",
            f"Suggested grade: {_or_not_evaluated(report.suggested_grade)} of 5.0",
            f"Status: {report.overall_status.value}",
        ]
        coverage = report.coverage_summary
        if coverage is not None:
            lines += [
                f"Criteria evaluated: {coverage.evaluated_criteria}/"
                f"{coverage.total_criteria}",
                f"Evaluated weight: {coverage.evaluated_weight:.4f}",
                f"Excluded weight: {coverage.excluded_weight:.4f}",
            ]
            if coverage.partial:
                lines.append(
                    "Coverage is partial; excluded weight was not silently "
                    "redistributed."
                )
        return "\n".join(lines)

    @staticmethod
    def _dimensions(report: EvaluationReport) -> str:
        if not report.dimension_results:
            return ""
        lines = ["Dimension | Weight | Score | Contribution | Status | Coverage"]
        for item in report.dimension_results:
            lines.append(
                f"{item.dimension_id} | {item.weight:.2f} | "
                f"{_or_not_evaluated(item.score)} | "
                f"{_or_not_evaluated(item.weighted_contribution)} | "
                f"{item.status.value} | {item.coverage:.2f}"
            )
        return "\n".join(lines)

    @staticmethod
    def _functional(report: EvaluationReport) -> str:
        if not report.requirement_results and not report.criterion_results:
            return ""
        lines: list[str] = []
        for requirement in report.requirement_results[:MAX_REQUIREMENTS]:
            lines.append(
                f"{requirement.requirement_id} | {requirement.title} | "
                f"weight {requirement.functional_weight:.3f} | "
                f"{requirement.status.value} | "
                f"{_or_not_evaluated(requirement.score)} | "
                f"cases {requirement.passed_cases}/{requirement.total_cases}"
            )
            for evidence in requirement.files_lines:
                lines.append(f"- evidence {evidence}")
            children = [
                item
                for item in report.criterion_results
                if item.requirement_id == requirement.requirement_id
            ][:MAX_CRITERIA_PER_REQUIREMENT]
            lines += _criterion_lines(children, report.evidence)
        if not lines:
            lines = _criterion_lines(
                [
                    item
                    for item in report.criterion_results
                    if item.dimension == "functional_requirements"
                ][:MAX_REQUIREMENTS],
                report.evidence,
            )
        return "\n".join(lines)

    @staticmethod
    def _architecture(report: EvaluationReport) -> str:
        if not report.architecture_results:
            return ""
        lines: list[str] = []
        for subdimension in report.architecture_results:
            lines.append(
                f"{subdimension.name} | D4 weight {subdimension.weight_in_d4:.2f} | "
                f"score {_or_not_evaluated(subdimension.score_5)} | "
                f"{subdimension.status.value} | coverage {subdimension.coverage:.2f}"
            )
            lines += _criterion_lines(subdimension.criteria, report.evidence)
        return "\n".join(lines)

    @staticmethod
    def _quality(report: EvaluationReport) -> str:
        summary = report.test_summary
        lines = [
            f"Tests executed: {summary.executed}",
            f"Passed/failed/skipped/errors: "
            f"{summary.passed}/{summary.failed}/{summary.skipped}/{summary.errors}",
            f"Requirements covered: {summary.covered_requirements}/"
            f"{summary.total_requirements} ({summary.coverage_ratio:.1%})",
        ]
        grouped: dict[tuple[str, str], int] = {}
        for finding in report.findings:
            key = (finding.severity, finding.rule_id)
            grouped[key] = grouped.get(key, 0) + 1
        for (severity, rule_id), count in list(grouped.items())[:MAX_FINDING_GROUPS]:
            lines.append(f"Finding group: {severity} {rule_id} x{count}")
        for run in report.tool_runs[:MAX_TOOL_RUNS]:
            artifact = f" artifact={run.output_artifact}" if run.output_artifact else ""
            limitation = f" limitation={run.limitation}" if run.limitation else ""
            lines.append(
                f"Tool: {run.tool_id} {run.execution_status}{artifact}{limitation}"
            )
        return "\n".join(lines)

    @staticmethod
    def _limitations(report: EvaluationReport) -> str:
        lines = [
            f"- {item.description} ({item.reason_code}; {item.coverage_impact})"
            for item in report.limitations
        ]
        lines += [
            f"- criterion {item.criterion_id}: {item.reason}"
            for item in report.criterion_results
            if item.status in NON_EVALUABLE_STATUSES and item.reason
        ]
        return "\n".join(lines)

    @staticmethod
    def _actions(report: EvaluationReport) -> str:
        if not report.priority_actions:
            return ""
        return "\n".join(
            f"- {item.text} [{item.target_id}; {item.impact}]"
            for item in report.priority_actions[:MAX_ACTIONS]
        )


def _criterion_lines(
    items: list[CriterionResult], evidence: list[EvidenceReference]
) -> list[str]:
    lines: list[str] = []
    for item in items:
        status = item.status.value
        score = _or_not_evaluated(item.score)
        reason = item.reason or item.reason_code or ""
        lines.append(
            f"- {item.criterion_id} {status} {score} weight={item.weight:.3f}"
            + (f": {reason}" if reason else "")
        )
        evidence_by_id = {ref.evidence_id: ref for ref in evidence}
        for evidence_id in item.evidence_ids[:MAX_EVIDENCE_PER_CRITERION]:
            ref = evidence_by_id.get(evidence_id)
            lines.append(f"  evidence {_evidence_label(ref, evidence_id)}")
    return lines


def _evidence_label(ref: EvidenceReference | None, evidence_id: str) -> str:
    if ref is None:
        return evidence_id
    location = _location(ref)
    summary = " ".join(ref.summary.split())[:120]
    return f"{evidence_id} {location}" + (f" {summary}" if summary else "")


def _location(ref: EvidenceReference) -> str:
    if not ref.path:
        return f"[{ref.type}]"
    start = ref.line_start if ref.line_start is not None else ref.line
    end = ref.line_end if ref.line_end is not None else ref.line
    if start is not None and end is not None:
        return f"{ref.path}:{start}-{end}"
    if ref.symbol:
        return f"{ref.path}::{ref.symbol}"
    return ref.path


def _legacy_sections(result: ExamResult) -> list[tuple[str, str]]:
    lines = [
        f"Student: {result.student_id}",
        f"Project: {result.project_id}",
        f"Exam attempt: {result.exam_attempt_id}",
        f"Raw score: {_or_not_evaluated(result.raw_score_50)} of 50",
        f"Suggested grade: {_or_not_evaluated(result.suggested_grade)} of 5.0",
    ]
    for dimension, score in result.dimension_scores.items():
        lines.append(f"{dimension}: {_or_not_evaluated(score)}")
    return [("1. Identification", "\n".join(lines))]


def _blocks(body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for chunk in body.split("\n"):
        text = chunk.strip()
        if not text:
            continue
        if text.startswith("- "):
            out.append(("li", text[2:]))
        elif text.startswith("  evidence "):
            out.append(("li", text.strip()))
        else:
            out.append(("p", text))
    return out


def _language_line(locale: str | None) -> str:
    if not locale:
        return ""
    from ..locale.models import LOCALE_LABELS

    return f"Language: {LOCALE_LABELS.get(locale, locale)} ({locale})"


def _or_not_evaluated(value: object) -> str:
    return "not evaluated" if value is None else str(value)


def _timestamp(value) -> str:
    return value.isoformat() if value is not None else ""


def _slug(value: str | None) -> str:
    return (value or "report").rsplit("://", 1)[-1]


__all__ = ["SECTIONS", "ExamReportGenerator"]
