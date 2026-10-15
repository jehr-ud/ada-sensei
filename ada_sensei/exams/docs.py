"""Exam documentation under ``docs/ada-sensei/exams/<exam_id>/`` (RQ-EXM-008/009).

ADA Sensei writes only into its own ``docs/ada-sensei/`` subtree. Every generated
file carries a marker so a later run can tell generated content apart from
student-authored content and refuse to overwrite the latter
(spec.md §Project docs directory).
"""

from __future__ import annotations

from pathlib import Path

from .models import ExamDefinition, ExamResult
from .rubric import EXAM_RUBRIC

#: Marks a file as ADA Sensei generated content (spec.md §Security and integrity).
GENERATED_MARKER = "<!-- generated-by: ada-sensei -->"

#: Root of the generated documentation subtree, relative to the project.
DOCS_ROOT = Path("docs") / "ada-sensei"

README_NAME = "README.md"
CONTEXT_NAME = "exam-context.md"
RUBRIC_NAME = "exam-rubric.md"
ARCHITECTURE_NAME = "architecture.md"
SUMMARY_NAME = "evaluation-summary.md"

#: Files written at exam start (RQ-EXM-009).
START_FILES = (README_NAME, CONTEXT_NAME, RUBRIC_NAME)
#: Files added after the exam finishes (spec.md §Project docs directory).
FINISH_FILES = ARCHITECTURE_NAME, SUMMARY_NAME


class DocsWriteError(Exception):
    """A generated file could not be written."""


class ExamDocs:
    """Read/write access to one exam's generated documentation directory."""

    def __init__(self, project_root: str | Path, exam_id: str) -> None:
        self.project_root = Path(project_root)
        self.exam_id = exam_id
        self.directory = self.project_root / DOCS_ROOT / _slug(exam_id)

    def ensure(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory

    def path(self, name: str) -> Path:
        return self.directory / name

    def write(self, name: str, body: str) -> Path:
        """Write a generated file, never overwriting non-generated content."""
        target = self.path(name)
        if target.exists() and not is_generated(target):
            raise DocsWriteError(
                f"refusing to overwrite student-authored file: {target}"
            )
        self.ensure()
        target.write_text(
            body if GENERATED_MARKER in body else f"{body}\n\n{GENERATED_MARKER}\n",
            encoding="utf-8",
        )
        return target

    def read(self, name: str) -> str:
        target = self.path(name)
        return target.read_text(encoding="utf-8") if target.exists() else ""

    def list_files(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(p for p in self.directory.iterdir() if p.is_file())


def is_generated(path: str | Path) -> bool:
    """True when the file carries the ADA Sensei generated marker."""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        return GENERATED_MARKER in target.read_text(encoding="utf-8")
    except OSError:
        return False


def _slug(exam_id: str) -> str:
    return exam_id.rsplit("://", 1)[-1] if "://" in exam_id else exam_id


class ExamDocsWriter:
    """Renders the exam documentation files (RQ-EXM-009)."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)

    def docs_for(self, exam_id: str) -> ExamDocs:
        return ExamDocs(self.project_root, exam_id)

    def write_start_docs(
        self, definition: ExamDefinition, docs: ExamDocs | None = None
    ) -> list[Path]:
        """Create the exam directory plus context, rubric, and README files."""
        target = docs or self.docs_for(definition.exam_id)
        target.ensure()
        return [
            target.write(README_NAME, render_readme(definition)),
            target.write(CONTEXT_NAME, render_context(definition)),
            target.write(RUBRIC_NAME, render_rubric(definition)),
        ]

    def write_finish_docs(
        self,
        result: ExamResult,
        definition: ExamDefinition,
        docs: ExamDocs | None = None,
    ) -> list[Path]:
        """Add the architecture and evaluation-summary files after finishing."""
        target = docs or self.docs_for(definition.exam_id)
        target.ensure()
        return [
            target.write(ARCHITECTURE_NAME, render_architecture(result)),
            target.write(SUMMARY_NAME, render_summary(result)),
        ]


# -- renderers ------------------------------------------------------------


def render_readme(definition: ExamDefinition) -> str:
    rules = definition.documentation_rules
    accepted = "\n".join(f"- `{g}`" for g in rules.accepted_globs) or "- (none)"
    required = "\n".join(f"- `{g}`" for g in rules.required_files) or "- (none)"
    return f"""# Exam `{definition.exam_id}`

{definition.title or "(untitled exam)"}

This directory is generated and maintained by ADA Sensei. Do not edit the
generated files; your own documentation belongs in the accepted locations below.

## Exam rules

- Rubric: `{definition.rubric_ref}`
- Allowed duration: {_format_limit(definition.allowed_duration_seconds, "seconds")}
- Allowed `/ask` count: {_format_limit(definition.allowed_ask_count, "asks")}
- Functional requirements: {len(definition.requirements)}

## Your documentation

ADA Sensei accepts your documentation at:

{accepted}

Required files:

{required}

Student documentation is treated as a claim you make about your work. It can
explain and structure your explanation, but it cannot override objective project
evidence.
"""


def render_context(definition: ExamDefinition) -> str:
    lines = [
        "# Exam context",
        "",
        f"- Exam id: `{definition.exam_id}`",
        f"- Version: `{definition.version}`",
        f"- Rubric: `{definition.rubric_ref}`",
        f"- Statement source: `{definition.statement_source}`",
        f"- Statement format: `{definition.statement_format.value}`",
        "",
        "## Functional requirements",
        "",
    ]
    if not definition.requirements:
        lines.append(
            "The instructor statement exposed no machine-readable requirements. "
            "Functional requirements are **not evaluated**; see the limitations "
            "in the final report."
        )
    else:
        lines.append("| id | requirement | weight | evidence expected |")
        lines.append("|---|---|---:|---|")
        for req in definition.requirements:
            expected = ", ".join(req.evidence_expectations) or "—"
            lines.append(
                f"| `{req.requirement_id}` | {req.description} | "
                f"{req.weight:g} | {expected} |"
            )
    if definition.original_source_path:
        lines += [
            "",
            f"Original instructor statement: `{definition.original_source_path}`",
        ]
    if definition.limitations:
        lines += ["", "## Limitations", ""]
        lines += [f"- {lim}" for lim in definition.limitations]
    return "\n".join(lines)


def render_rubric(definition: ExamDefinition) -> str:
    lines = [
        "# Exam rubric",
        "",
        f"Rubric `{definition.rubric_ref}` is applied by the shared rubric engine "
        "from `006-evaluate`. ADA Sensei does not invent weights.",
        "",
        "| dimension | weight | description |",
        "|---|---:|---|",
    ]
    for dim in EXAM_RUBRIC.dimensions:
        lines.append(f"| `{dim.id}` | {dim.weight:.0%} | {dim.description} |")
    process = EXAM_RUBRIC.dimension("exam_process")
    lines += ["", "### Exam process subcriteria", ""]
    for sub in process.subcriteria:
        lines.append(
            f"- `{sub.id}` — {sub.weight:.0%} of exam process "
            f"({sub.weight * process.weight:.0%} of the exam): {sub.description}"
        )
    lines += [
        "",
        "The raw score is computed as "
        "`50 × Σ(weight × score / 4) / Σ(weight of evaluated dimensions)`, and "
        "the suggested grade is `round(1.0 + (raw_score / 50) × 4.0, 1)`.",
        "",
        "Dimensions without sufficient evidence are marked *not evaluated* and "
        "leave the denominator. They never count as a pass.",
    ]
    return "\n".join(lines)


def render_architecture(result: ExamResult) -> str:
    report = result.architecture_report
    lines = ["# Architecture", ""]
    if report is None:
        return "\n".join(
            lines
            + [
                "No architecture analysis was produced; see the limitations in "
                "the final report.",
            ]
        )
    if report.narrative:
        lines += [report.narrative, ""]
    for kind, title in (
        ("observed", "Observed in the project"),
        ("documented", "Documented by the student"),
        ("inferred", "Inferred interpretation"),
    ):
        claims = report.by_kind(kind)
        lines += [f"## {title}", ""]
        if not claims:
            lines += ["_(none)_", ""]
            continue
        for claim in claims:
            refs = ", ".join(f"`{r}`" for r in claim.evidence_refs) or "—"
            lines.append(f"- {claim.claim} ({refs})")
        lines.append("")
    if report.unsupported_claims:
        lines += ["## Claims excluded as unsupported", ""]
        lines += [
            f"- {c.claim} — {c.reason}" for c in report.unsupported_claims
        ]
        lines.append("")
    return "\n".join(lines)


def render_summary(result: ExamResult) -> str:
    raw = result.raw_score_50
    grade = result.suggested_grade
    lines = [
        "# Evaluation summary",
        "",
        f"- Exam attempt: `{result.exam_attempt_id}`",
        f"- Rubric: `{result.rubric_ref}`",
        f"- Raw score: {raw if raw is not None else 'not evaluated'} / "
        f"{result.score_calculation.max_raw_score if result.score_calculation else 50}",
        f"- Suggested grade: {grade if grade is not None else 'not evaluated'} / 5.0",
        "",
        f"_{result.grade_disclosure}_",
        "",
        "## Dimension scores",
        "",
        "| dimension | score |",
        "|---|---:|",
    ]
    for dimension, score in result.dimension_scores.items():
        shown = "not evaluated" if score is None else score
        lines.append(f"| `{dimension}` | {shown} |")
    for title, items in (
        ("Strengths", result.strengths),
        ("Weaknesses", result.weaknesses),
        ("Recommendations", result.recommendations),
    ):
        lines += ["", f"## {title}", ""]
        lines += [f"- {item}" for item in items] or ["_(none)_"]
    if result.limitations:
        lines += ["", "## Limitations", ""]
        lines += [f"- {lim}" for lim in result.limitations]
    return "\n".join(lines)


def _format_limit(value: int | None, unit: str) -> str:
    return f"{value} {unit}" if value is not None else "not defined"


__all__ = [
    "ARCHITECTURE_NAME",
    "CONTEXT_NAME",
    "DOCS_ROOT",
    "DocsWriteError",
    "ExamDocs",
    "ExamDocsWriter",
    "FINISH_FILES",
    "GENERATED_MARKER",
    "README_NAME",
    "RUBRIC_NAME",
    "START_FILES",
    "SUMMARY_NAME",
    "is_generated",
    "render_architecture",
    "render_context",
    "render_readme",
    "render_rubric",
    "render_summary",
]
