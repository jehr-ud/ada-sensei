"""Evidence-to-requirement matching, callable on its own (RQ-EVA-005/006/033).

The matcher produces traceable associations: every criterion records the
``ev://`` ids backing it, and evidence no requirement claimed is preserved as
unmatched instead of being dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import EvaluationCriterion, Evidence, Exercise, NotEvaluatedReason
from .models import EvidenceContext
from .rubric import (
    requirement_not_evaluated_reason,
    score_requirement,
)

#: Words shorter than this carry no matching signal.
MIN_TOKEN_LEN = 4


@dataclass
class RequirementMatch:
    """Traceable result of matching one context against requirements."""

    criteria: list[EvaluationCriterion] = field(default_factory=list)
    matched_evidence_ids: list[str] = field(default_factory=list)
    unmatched_evidence: list[Evidence] = field(default_factory=list)

    def criteria_for(self, requirement_id: str) -> list[EvaluationCriterion]:
        return [c for c in self.criteria if c.requirement_id == requirement_id]


class RequirementMatcher:
    """Maps evidence onto ``req://`` identifiers and scores each requirement."""

    def __init__(self, exercise: Exercise | None) -> None:
        self.exercise = exercise

    def match(
        self,
        evidence: EvidenceContext,
        *,
        build_failed: bool = False,
    ) -> RequirementMatch:
        if self.exercise is None or not self.exercise.requirements:
            return RequirementMatch(unmatched_evidence=list(evidence.evidence))

        build_evidence = self._build_evidence(evidence)
        req_ids = [r.id for r in self.exercise.requirements]
        default_weight = 1.0 / len(req_ids) if req_ids else 0.0
        declared = {
            c.requirement_id: c.weight
            for c in self.exercise.evaluation_criteria
            if c.requirement_id
        }

        criteria: list[EvaluationCriterion] = []
        claimed: set[str] = set()
        for requirement in self.exercise.requirements:
            matched = self._evidence_for_requirement(
                requirement.summary, evidence, build_evidence
            )
            claimed.update(e.id for e in matched if e.id)
            criterion = EvaluationCriterion(
                requirement_id=requirement.id,
                dimension="functional_requirements",
                weight=declared.get(requirement.id, default_weight),
                evidence=matched,
                evidence_refs=[e.id for e in matched if e.id],
            )
            if build_failed:
                criterion.score = None
                criterion.note = "build failed; not evaluated"
                # RQ-EVA-018: the blocking cause is recorded explicitly, so a
                # failed build is never reported as merely "no evidence".
                criterion.not_evaluated_reason = NotEvaluatedReason.build_failed
            else:
                criterion.score = score_requirement(criterion)
                if criterion.score is None:
                    criterion.not_evaluated_reason = (
                        requirement_not_evaluated_reason(criterion)
                    )
            criteria.append(criterion)

        unmatched = [e for e in evidence.evidence if e.id not in claimed]
        return RequirementMatch(
            criteria=criteria,
            matched_evidence_ids=sorted(claimed),
            unmatched_evidence=unmatched,
        )

    @staticmethod
    def _build_evidence(evidence: EvidenceContext) -> Evidence | None:
        build = evidence.by_group("compilation")
        return build[0] if build else None

    @staticmethod
    def _evidence_for_requirement(
        summary: str,
        evidence: EvidenceContext,
        build_evidence: Evidence | None,
    ) -> list[Evidence]:
        matched: list[Evidence] = []
        if build_evidence is not None and build_evidence.status == "pass":
            matched.append(build_evidence)
        words = {w for w in summary.lower().split() if len(w) > MIN_TOKEN_LEN}
        for item in evidence.by_group("structure"):
            if item.file and any(w in item.file.lower() for w in words):
                matched.append(item)
        for item in evidence.by_group("unit_test"):
            if any(w in (item.message or "").lower() for w in words):
                matched.append(item)
        if not words:
            matched.extend(evidence.by_group("unit_test"))
        return matched


__all__ = ["RequirementMatch", "RequirementMatcher"]
