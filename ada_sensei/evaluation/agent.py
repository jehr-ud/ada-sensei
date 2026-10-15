"""Structured LLM interpretation of collected evaluation evidence.

The agent interprets; it never supplies evidence. RQ-EVA-034: every structured
result is schema validated with a maximum of 3 total attempts. RQ-EVA-035: any
claim that cannot be grounded in the available ``ev://`` references is reported
as an unsupported claim instead of being accepted as evidence.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..llm.base import LLMClient
from ..llm.pipeline import StructuredOutputError, StructuredPipeline
from ..models import UnsupportedClaim
from .models import EvidenceContext

#: The agent may not restate or override deterministic scores; it only reads
#: them. Anything the LLM returns about a score is informational.
MAX_EVIDENCE_PROMPTED = 40


class GroundedClaim(BaseModel):
    """A qualitative statement that must cite the evidence it rests on."""

    claim: str
    #: ``ev://`` ids from the evidence context. Empty means the LLM asserted
    #: something with no evidence behind it.
    evidence_refs: list[str] = Field(default_factory=list)
    kind: str = "finding"


class EvaluationInterpretation(BaseModel):
    """Schema the evaluation agent must return (design.md §5)."""

    strengths: list[GroundedClaim] = Field(default_factory=list)
    weaknesses: list[GroundedClaim] = Field(default_factory=list)
    recommendations: list[GroundedClaim] = Field(default_factory=list)
    feedback: str = ""
    next_learning_activity: str = ""
    #: Free-form narrative claims; each is also grounding-checked.
    findings: list[GroundedClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class GroundedInterpretation(BaseModel):
    """An accepted interpretation plus the claims that were rejected.

    ``interpretation`` holds only claims whose ``evidence_refs`` resolved against
    the evidence context; everything else lives in ``unsupported_claims``.
    """

    interpretation: EvaluationInterpretation
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)

    def accepted_claims(self) -> list[GroundedClaim]:
        interp = self.interpretation
        return [
            *interp.strengths,
            *interp.weaknesses,
            *interp.recommendations,
            *interp.findings,
        ]

    def strengths(self) -> list[str]:
        return [c.claim for c in self.interpretation.strengths]

    def weaknesses(self) -> list[str]:
        return [c.claim for c in self.interpretation.weaknesses]

    def recommendations(self) -> list[str]:
        return [c.claim for c in self.interpretation.recommendations]

    def findings(self) -> list[str]:
        return [c.claim for c in self.interpretation.findings]


class EvaluationAgent:
    """Builds the prompt, runs the structured pipeline, grounds the output."""

    SYSTEM = (
        "You are ADA Sensei's evaluation interpreter. You receive objective "
        "evidence and deterministic dimension scores. You interpret them "
        "pedagogically. You MUST NOT invent evidence, MUST NOT invent "
        "components, and MUST NOT change the given scores. Every strength, "
        "weakness, recommendation, and finding MUST cite one or more evidence "
        "ids from the supplied evidence list in its evidence_refs field; a "
        "claim you cannot ground MUST be omitted rather than asserted. "
        "Return strictly valid JSON matching the EvaluationInterpretation "
        "schema without markdown fences."
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
        context: EvidenceContext,
        dimension_scores: dict[str, float | None],
    ) -> GroundedInterpretation:
        """Interpret evidence, grounding every claim in a real evidence id."""
        if self.client is None:
            return GroundedInterpretation(
                interpretation=EvaluationInterpretation(
                    feedback="LLM interpretation unavailable (no LLM client).",
                    recommendations=[],
                    limitations=["no LLM client available for interpretation"],
                )
            )
        pipeline = StructuredPipeline(
            self.client,
            max_attempts=self.max_attempts,
            temperature=(
                self.temperature if self.temperature is not None else 0.2
            ),
        )
        interpretation = pipeline.run(
            self.messages(context, dimension_scores),
            EvaluationInterpretation,
            model=self.model,
        )
        return self.ground(interpretation, context)

    def messages(
        self,
        context: EvidenceContext,
        dimension_scores: dict[str, float | None],
    ) -> list[dict[str, str]]:
        evidence_summary = "\n".join(
            f"- {e.id} [{e.source}/{e.type}/{e.status}] {e.message[:200]}"
            for e in context.evidence[:MAX_EVIDENCE_PROMPTED]
            if e.id
        ) or "(no evidence)"
        dimension_summary = ", ".join(
            f"{k}={v}" for k, v in sorted(dimension_scores.items())
        )
        limitations = "\n".join(f"- {lim}" for lim in context.limitations) or "(none)"
        return [
            {"role": "system", "content": self.SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Rubric: {context.project_id or '(unknown project)'}\n"
                    f"Deterministic dimension scores (do not change):\n"
                    f"{dimension_summary or '(none evaluated)'}\n\n"
                    f"Known limitations:\n{limitations}\n\n"
                    f"Evidence (cite these ids in evidence_refs):\n"
                    f"{evidence_summary}\n\n"
                    "Interpret only; do not invent evidence and do not change "
                    "scores."
                ),
            },
        ]

    @staticmethod
    def ground(
        interpretation: EvaluationInterpretation, context: EvidenceContext
    ) -> GroundedInterpretation:
        """Drop and report every claim whose evidence references do not resolve.

        RQ-EVA-035: unsupported claims are identified in the result instead of
        being silently treated as evidence.
        """
        known = context.ids()
        unsupported: list[UnsupportedClaim] = []
        accepted: dict[str, list[GroundedClaim]] = {
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "findings": [],
        }
        groups = (
            ("strengths", interpretation.strengths),
            ("weaknesses", interpretation.weaknesses),
            ("recommendations", interpretation.recommendations),
            ("findings", interpretation.findings),
        )
        for kind, claims in groups:
            for claim in claims:
                reason = _unsupported_reason(claim, known)
                if reason is None:
                    accepted[kind].append(claim)
                    continue
                unsupported.append(
                    UnsupportedClaim(claim=claim.claim, kind=kind, reason=reason)
                )
        return GroundedInterpretation(
            interpretation=EvaluationInterpretation(
                strengths=accepted["strengths"],
                weaknesses=accepted["weaknesses"],
                recommendations=accepted["recommendations"],
                feedback=interpretation.feedback,
                next_learning_activity=interpretation.next_learning_activity,
                findings=accepted["findings"],
                limitations=list(interpretation.limitations),
            ),
            unsupported_claims=unsupported,
        )


def _unsupported_reason(claim: GroundedClaim, known: set[str]) -> str | None:
    if not claim.evidence_refs:
        return "claim cites no evidence id"
    unresolved = [ref for ref in claim.evidence_refs if ref not in known]
    if unresolved:
        return f"claim cites unknown evidence id(s): {', '.join(unresolved)}"
    return None


def unavailable_interpretation(reason: str) -> GroundedInterpretation:
    """Interpretation used when the structured pipeline failed (RQ-EVA-034).

    The failure is explicit; deterministic scoring is unaffected.
    """
    return GroundedInterpretation(
        interpretation=EvaluationInterpretation(
            feedback=(
                "LLM interpretation failed; deterministic scoring remains."
            ),
            limitations=[reason],
        )
    )


__all__ = [
    "EvaluationAgent",
    "EvaluationInterpretation",
    "GroundedClaim",
    "GroundedInterpretation",
    "StructuredOutputError",
    "unavailable_interpretation",
]
