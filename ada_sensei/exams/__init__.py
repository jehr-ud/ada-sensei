"""``007-examine`` — the exam overlay over the reusable evaluation engine.

``exam-init`` adds an exam lifecycle, process evidence, an architecture report and a
PDF on top of ``006-evaluate``. It reuses the same ``EvaluationEngine``,
``RubricEngine`` and structured-output pipeline and supplies its own versioned
``RubricDefinition`` (``exam-default:v1``), so project evaluation has exactly one
implementation (ADR-022, ADR-023, ADR-024).
"""

from .definition import ExamDefinitionLoader
from .docs import DocsWriteError, ExamDocs, ExamDocsWriter
from .events import EVENT_MAP, ExamEventBridge, ExamEventLog
from .lifecycle import TRANSITIONS, ExamLifecycle
from .models import (
    ADMINISTRATIVE_FIELDS,
    ASK_NON_COUNTING_EVENTS,
    ASK_SUCCESS_EVENTS,
    DEFAULT_EXAM_RUBRIC_REF,
    SUGGESTED_GRADE_LABEL,
    ArchitectureClaim,
    ArchitectureReport,
    DocumentationRules,
    ExamAttempt,
    ExamAttemptImmutableError,
    ExamAttemptNotFoundError,
    ExamDefinition,
    ExamDefinitionError,
    ExamError,
    ExamEvent,
    ExamEventType,
    ExamRequirement,
    ExamResult,
    ExamStateError,
    ExamStatus,
    ProcessMetrics,
    ScoreCalculation,
    ScoreLine,
    StatementFormat,
    requirement_id_for,
)
from .pdf import SimplePdfWriter
from .pdftext import PdfTextExtractionError, extract_text, extract_text_file
from .process import (
    ask_usage_score,
    compute_duration_seconds,
    compute_overtime,
    duration_score,
    process_metrics,
)
from .report import SECTIONS, ExamReportGenerator
from .rubric import EXAM_RUBRIC, resolve_rubric
from .scoring import ExamScorer, suggested_grade
from .store import ExamStore

__all__ = [
    "ADMINISTRATIVE_FIELDS",
    "ASK_NON_COUNTING_EVENTS",
    "ASK_SUCCESS_EVENTS",
    "DEFAULT_EXAM_RUBRIC_REF",
    "EVENT_MAP",
    "EXAM_RUBRIC",
    "SECTIONS",
    "SUGGESTED_GRADE_LABEL",
    "TRANSITIONS",
    "ArchitectureClaim",
    "ArchitectureReport",
    "DocsWriteError",
    "DocumentationRules",
    "ExamAttempt",
    "ExamAttemptImmutableError",
    "ExamAttemptNotFoundError",
    "ExamDefinition",
    "ExamDefinitionError",
    "ExamDefinitionLoader",
    "ExamDocs",
    "ExamDocsWriter",
    "ExamError",
    "ExamEvent",
    "ExamEventBridge",
    "ExamEventLog",
    "ExamEventType",
    "ExamLifecycle",
    "ExamReportGenerator",
    "ExamRequirement",
    "ExamResult",
    "ExamScorer",
    "ExamStateError",
    "ExamStatus",
    "ExamStore",
    "PdfTextExtractionError",
    "ProcessMetrics",
    "ScoreCalculation",
    "ScoreLine",
    "SimplePdfWriter",
    "StatementFormat",
    "ask_usage_score",
    "compute_duration_seconds",
    "compute_overtime",
    "duration_score",
    "extract_text",
    "extract_text_file",
    "process_metrics",
    "requirement_id_for",
    "resolve_rubric",
    "suggested_grade",
]
