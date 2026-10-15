"""Structured LLM interpretation for the exam (RQ-EXM-023, RQ-EXM-025, RQ-EXM-030).

The exam reuses the shared ``StructuredPipeline`` from ``006-evaluate`` — LLM →
parser → schema validation → retry → final failure, at most 3 total attempts. The
agent is qualitative only: it never sees, proposes, or overrides a score, and it
may not invent an architecture component. Every claim it returns must cite
evidence the collector actually produced; anything else is reported as an
unsupported claim rather than believed.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..evaluation import (
    EvidenceContext,
    GroundedClaim,
    unavailable_interpretation,
)
from ..evaluation.agent import EvaluationAgent, EvaluationInterpretation
from ..llm.base import LLMClient
from ..llm.pipeline import StructuredPipeline
from ..models import UnsupportedClaim
from .models import ArchitectureClaim, ExamDefinition, ProcessMetrics

#: The prompt never includes more evidence than this (context safety).
MAX_EVIDENCE_PROMPTED = 40


class ExamInterpretation(BaseModel):
    """Schema the exam interpreter must return."""

    strengths: list[GroundedClaim] = Field(default_factory=list)
    weaknesses: list[GroundedClaim] = Field(default_factory=list)
    recommendations: list[GroundedClaim] = Field(default_factory=list)
    findings: list[GroundedClaim] = Field(default_factory=list)
    feedback: str = ""
    next_learning_activity: str = ""
    limitations: list[str] = Field(default_factory=list)
    #: Architecture statements the model infers; each is grounding-checked and
    #: must declare ``kind: "inferred"``.
    architecture: list[GroundedClaim] = Field(default_factory=list)


class GroundedExamInterpretation(BaseModel):
    """Accepted interpretation plus everything that was rejected.

    Rejections from the qualitative claims and from the architecture claims are
    both kept here, so nothing the model invented is silently accepted
    (RQ-EXM-025, RQ-EXM-030).
    """

    interpretation: ExamInterpretation
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    architecture_claims: list[ArchitectureClaim] = Field(default_factory=list)

    def strengths(self) -> list[str]:
        return [c.claim for c in self.interpretation.strengths]

    def weaknesses(self) -> list[str]:
        return [c.claim for c in self.interpretation.weaknesses]

    def recommendations(self) -> list[str]:
        return [c.claim for c in self.interpretation.recommendations]

    def findings(self) -> list[str]:
        return [c.claim for c in self.interpretation.findings]

    def unsupported(self) -> list:
        return list(self.unsupported_claims)


class ExamInterpretationAgent:
    """Qualitative exam interpretation, grounded in collected evidence."""

    SYSTEM = (
        "You are ADA Sensei's exam interpreter. You receive an authoritative "
        "exam statement, objective project evidence, the student's own "
        "documentation, exam process metrics, and already-computed dimension "
        "scores. You interpret them pedagogically. You MUST NOT invent "
        "evidence, MUST NOT invent Android components or relationships that are "
        "not in the supplied evidence, and MUST NOT change or restate any "
        "score. Every strength, weakness, recommendation, finding and "
        "architecture statement MUST cite one or more reference ids from the "
        "supplied lists in its evidence_refs field; omit anything you cannot "
        "ground. Ask-usage measures use of the tutor, not honesty, and you MUST "
        "NOT suggest dishonesty from it. Return strictly valid JSON matching the "
        "ExamInterpretation schema without markdown fences."
    )

    def __init__(
        self,
        client: LLMClient | None,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_attempts = max_attempts

    def interpret(
        self,
        exam: ExamDefinition,
        evidence: EvidenceContext,
        metrics: ProcessMetrics,
        dimension_scores: dict[str, float | None],
        documentation: list[str] | None = None,
    ) -> GroundedExamInterpretation:
        if self.client is None:
            return self._unavailable("no LLM client available for exam interpretation")
        pipeline = StructuredPipeline(
            self.client,
            max_attempts=self.max_attempts,
            temperature=(
                self.temperature if self.temperature is not None else 0.2
            ),
        )
        interpretation = pipeline.run(
            self.messages(exam, evidence, metrics, dimension_scores, documentation),
            ExamInterpretation,
            model=self.model,
        )
        return self.ground(interpretation, evidence, documentation or [])

    # -- prompt -----------------------------------------------------------

    def messages(
        self,
        exam: ExamDefinition,
        evidence: EvidenceContext,
        metrics: ProcessMetrics,
        dimension_scores: dict[str, float | None],
        documentation: list[str] | None = None,
    ) -> list[dict[str, str]]:
        evidence_lines = "\n".join(
            f"- {e.id} [{e.source}/{e.type}/{e.status}] "
            f"{(e.file or '')} {e.message[:200]}".rstrip()
            for e in evidence.evidence[:MAX_EVIDENCE_PROMPTED]
            if e.id
        ) or "(no evidence)"
        requirement_lines = "\n".join(
            f"- {r.requirement_id}: {r.description}"
            for r in exam.requirements
        ) or "(the statement exposed no machine-readable requirements)"
        docs = "\n".join(f"- doc://{d}" for d in documentation or []) or "(none)"
        metrics_text = (
            f"duration={metrics.duration_seconds}s of "
            f"{metrics.allowed_duration_seconds}s allowed, "
            f"asks={metrics.ask_count} of {metrics.allowed_ask_count} allowed"
        )
        return [
            {"role": "system", "content": self.SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Exam: {exam.title or exam.exam_id} ({exam.exam_id})\n"
                    f"Rubric: {exam.rubric_ref}\n\n"
                    f"Instructor requirements:\n{requirement_lines}\n\n"
                    f"Deterministic dimension scores (do not change): "
                    f"{_scores(dimension_scores)}\n\n"
                    f"Exam process metrics (from application events, not claims): "
                    f"{metrics_text}\n\n"
                    f"Student documentation you may cite as doc:// references:\n"
                    f"{docs}\n\n"
                    f"Project evidence (cite these ev:// ids):\n{evidence_lines}\n\n"
                    "Interpret only. Do not invent components and do not change "
                    "scores."
                ),
            },
        ]

    # -- grounding --------------------------------------------------------

    @staticmethod
    def ground(
        interpretation: ExamInterpretation,
        evidence: EvidenceContext,
        documentation: list[str],
    ) -> GroundedExamInterpretation:
        """Validate every claim against the evidence that was actually collected.

        Qualitative claims go through the shared grounding validator, architecture
        claims through ``_ground_architecture``; both sets of rejections are
        reported, never dropped.
        """
        known = evidence.ids() | {f"doc://{d}" for d in documentation}
        base = EvaluationAgent.ground(
            _as_evaluation_interpretation(interpretation), evidence
        )
        kept = base.interpretation
        merged = ExamInterpretation(
            strengths=kept.strengths,
            weaknesses=kept.weaknesses,
            recommendations=kept.recommendations,
            findings=kept.findings,
            feedback=interpretation.feedback,
            next_learning_activity=interpretation.next_learning_activity,
            limitations=list(interpretation.limitations),
        )
        architecture, rejected = _ground_architecture(
            interpretation.architecture, known
        )
        return GroundedExamInterpretation(
            interpretation=merged,
            architecture_claims=architecture,
            unsupported_claims=[*base.unsupported_claims, *rejected],
        )

    def _unavailable(self, reason: str) -> GroundedExamInterpretation:
        fallback = unavailable_interpretation(reason)
        return GroundedExamInterpretation(
            interpretation=ExamInterpretation(
                feedback=fallback.interpretation.feedback,
                limitations=list(fallback.interpretation.limitations),
            )
        )


def _ground_architecture(
    claims: list[GroundedClaim], known: set[str]
) -> tuple[list[ArchitectureClaim], list[UnsupportedClaim]]:
    """Keep inferred architecture claims only when they cite real evidence."""
    kept: list[ArchitectureClaim] = []
    rejected: list[UnsupportedClaim] = []
    for claim in claims:
        resolved = [r for r in claim.evidence_refs if r in known]
        if not resolved:
            rejected.append(
                UnsupportedClaim(
                    claim=claim.claim,
                    kind="architecture",
                    reason=(
                        "no supplied evidence id was cited "
                        f"(referenced: {', '.join(claim.evidence_refs) or 'nothing'})"
                    ),
                )
            )
            continue
        kept.append(
            ArchitectureClaim(
                claim=claim.claim,
                kind="inferred",
                evidence_refs=resolved,
                source="LLM inference",
            )
        )
    return kept, rejected


def _as_evaluation_interpretation(
    interpretation: ExamInterpretation,
) -> EvaluationInterpretation:
    """Reuse the shared grounding validator for the non-architecture claims."""
    return EvaluationInterpretation(
        strengths=interpretation.strengths,
        weaknesses=interpretation.weaknesses,
        recommendations=interpretation.recommendations,
        findings=interpretation.findings,
        feedback=interpretation.feedback,
        next_learning_activity=interpretation.next_learning_activity,
        limitations=interpretation.limitations,
    )


def _scores(dimension_scores: dict[str, float | None]) -> str:
    if not dimension_scores:
        return "(none evaluated)"
    return ", ".join(
        f"{k}={v if v is not None else 'not evaluated'}"
        for k, v in sorted(dimension_scores.items())
    )


__all__ = [
    "ExamInterpretation",
    "ExamInterpretationAgent",
    "GroundedExamInterpretation",
    "MAX_EVIDENCE_PROMPTED",
]
