"""LLM evaluators for semantic criterion decisions (006-evaluate v2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..llm.base import LLMClient, LLMError
from ..llm.pipeline import StructuredPipeline
from .models import CriterionStatus, EvidenceContext, LLMRunMetadata
from .rubric import CLEAN_ARCHITECTURE_CRITERIA, MVVM_CRITERIA

DEFAULT_MODEL = "qwen2.5-coder:7b"
PROVIDER = "ollama"
TEMPERATURE = 0.0
MAX_ATTEMPTS = 3
PROMPT_ID = "llm-criterion-evaluation"
PROMPT_VERSION = "2.1.0"
MAX_EVIDENCE_ITEMS = 60

LLM_STATUSES = ("PASS", "PARTIAL", "FAIL", "NOT_EVALUATED")


class EvaluationCriterionInput(BaseModel):
    criterion_id: str
    description: str
    requirement_id: str | None = None
    dimension: str = "functional_requirements"
    subdimension: str | None = None


class LLMCriterionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    status: Literal["PASS", "PARTIAL", "FAIL", "NOT_EVALUATED"]
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=0)
    limitations: list[str] = Field(min_length=0)
    recommended_action: str = Field()
    confidence: float = Field(ge=0.0, le=1.0)
    reason_code: str | None = None

    @model_validator(mode="after")
    def _decision_needs_evidence_or_reason(self) -> LLMCriterionDecision:
        if self.status in {"PASS", "PARTIAL", "FAIL"} and not self.evidence_ids:
            raise ValueError(
                f"{self.criterion_id}: {self.status} requires evidence_ids"
            )
        return self


class CriterionDecisionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: list[LLMCriterionDecision] = Field()


class ArchitectureDecisionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clean_architecture: list[LLMCriterionDecision] = Field(default_factory=list)
    mvvm: list[LLMCriterionDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def _requires_decisions(self) -> ArchitectureDecisionBatch:
        if not self.clean_architecture and not self.mvvm:
            raise ValueError("at least one architecture decision is required")
        return self


@dataclass
class DecisionBatch:
    decisions: list[LLMCriterionDecision]
    run: LLMRunMetadata


class EvidenceValidationError(Exception):
    pass


def _evidence_lines(context: EvidenceContext) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for item in context.evidence[:MAX_EVIDENCE_ITEMS]:
        lines.append(
            {
                "evidence_id": item.id,
                "type": item.type,
                "path": item.file,
                "symbol": item.symbol,
                "line_start": (
                    item.line_start if item.line_start is not None else item.line
                ),
                "line_end": (
                    item.line_end if item.line_end is not None else item.line
                ),
                "summary": item.message[:240],
                "excerpt": item.excerpt[:180],
                "status": item.status,
            }
        )
    return lines


def _criteria_lines(criteria: list[EvaluationCriterionInput]) -> list[dict[str, Any]]:
    return [
        {
            "criterion_id": item.criterion_id,
            "description": item.description,
            "subdimension": item.subdimension,
        }
        for item in criteria
    ]


def _system_prompt() -> str:
    return (
        "You evaluate Android project evidence for ADA Sensei. Decide each "
        "acceptance criterion independently using only the supplied evidence "
        "ids. Never invent paths, symbols, lines or behavior. A class, folder, "
        "comment or dependency name alone is not proof of behavior. A test "
        "only proves the scenario it executes. Static inspection of runtime, "
        "remote or visual behavior is at most PARTIAL when part is demonstrable "
        "and NOT_EVALUATED otherwise. Do not assign scores, weights or grades. "
        "Return strictly valid JSON matching the requested schema. Every "
        "decision object MUST include criterion_id (string), status (one of "
        "PASS, PARTIAL, FAIL, NOT_EVALUATED), reason (non-empty string), "
        "evidence_ids (array of strings), limitations (array of strings), "
        "recommended_action (string) and confidence (number from 0 to 1). "
        "reason_code is optional. Do not use aliases or omit required fields. "
        "For functional criteria return exactly {\"criteria\": [decision, ...]}. "
        "For architecture return exactly {\"clean_architecture\": [decision, "
        "...], \"mvvm\": [decision, ...]}. Do not return a bare decision object. "
        "PASS, PARTIAL and FAIL require at least one evidence_id; "
        "NOT_EVALUATED requires a limitation."
    )


def _metadata(
    *,
    started: datetime,
    duration: float,
    attempts: int,
    validation_status: str,
    model: str = DEFAULT_MODEL,
    prompt_version: str = PROMPT_VERSION,
    limitations: list[str] | None = None,
) -> LLMRunMetadata:
    return LLMRunMetadata(
        provider=PROVIDER,
        model_id=model,
        prompt_id=PROMPT_ID,
        prompt_version=prompt_version,
        temperature=TEMPERATURE,
        attempts=attempts,
        validation_status=validation_status,
        started_at=started,
        duration_seconds=round(duration, 3),
        limitations=list(limitations or []),
    )


def _not_evaluated(
    criteria: list[EvaluationCriterionInput], reason_code: str, reason: str
) -> list[LLMCriterionDecision]:
    return [
        LLMCriterionDecision(
            criterion_id=item.criterion_id,
            status=CriterionStatus.NOT_EVALUATED.value,
            reason=reason,
            evidence_ids=[],
            limitations=[reason_code],
            recommended_action="provide the missing model or valid evidence",
            confidence=0.0,
            reason_code=reason_code,
        )
        for item in criteria
    ]


def _expected(
    criteria: list[EvaluationCriterionInput],
) -> dict[str, EvaluationCriterionInput]:
    return {item.criterion_id: item for item in criteria}


def _validate_decisions(
    decisions: list[LLMCriterionDecision],
    criteria: list[EvaluationCriterionInput],
    context: EvidenceContext,
) -> tuple[list[LLMCriterionDecision], list[str]]:
    expected = _expected(criteria)
    by_id: dict[str, LLMCriterionDecision] = {}
    issues: list[str] = []
    for decision in decisions:
        if decision.criterion_id in by_id:
            issues.append(f"duplicate decision for {decision.criterion_id}")
            continue
        if decision.criterion_id not in expected:
            issues.append(f"unknown decision criterion {decision.criterion_id}")
            continue
        clean, decision_issues = _validate_evidence_refs(decision, context)
        issues.extend(decision_issues)
        by_id[decision.criterion_id] = clean

    accepted: list[LLMCriterionDecision] = []
    for item in criteria:
        decision = by_id.get(item.criterion_id)
        if decision is None:
            issues.append(f"missing decision for {item.criterion_id}")
            accepted.append(
                LLMCriterionDecision(
                    criterion_id=item.criterion_id,
                    status=CriterionStatus.NOT_EVALUATED.value,
                    reason="the model returned no decision for this criterion",
                    evidence_ids=[],
                    reason_code="LLM_INVALID_OUTPUT",
                    limitations=["missing criterion decision"],
                    recommended_action="rerun the evaluation with a valid model",
                    confidence=0.0,
                )
            )
            continue
        if decision.status in {"PASS", "PARTIAL", "FAIL"} and not decision.evidence_ids:
            decision = decision.model_copy(
                update={
                    "status": CriterionStatus.NOT_EVALUATED.value,
                    "reason": "no valid evidence was cited for this decision",
                    "reason_code": "MISSING_EVIDENCE",
                    "limitations": [*decision.limitations, "missing evidence"],
                }
            )
        accepted.append(decision)
    return accepted, issues


def _validate_evidence_refs(
    decision: LLMCriterionDecision, context: EvidenceContext
) -> tuple[LLMCriterionDecision, list[str]]:
    known = {item.id for item in context.evidence if item.id}
    valid: list[str] = []
    issues: list[str] = []
    for evidence_id in decision.evidence_ids:
        item = next((e for e in context.evidence if e.id == evidence_id), None)
        if item is None or evidence_id not in known:
            issues.append(
                f"{decision.criterion_id}: unknown evidence id {evidence_id}"
            )
            continue
        if item.file and Path(item.file).is_absolute():
            issues.append(f"{decision.criterion_id}: absolute evidence path")
            continue
        start = item.line_start if item.line_start is not None else item.line
        end = item.line_end if item.line_end is not None else item.line
        if start is not None and end is not None:
            if start < 1 or end < start:
                issues.append(
                    f"{decision.criterion_id}: invalid evidence line range "
                    f"{start}-{end}"
                )
                continue
            if context.project_path and item.file:
                source = Path(context.project_path) / item.file
                if source.is_file():
                    count = len(
                        source.read_text(
                            encoding="utf-8", errors="replace"
                        ).splitlines()
                    )
                    if end > count:
                        issues.append(
                            f"{decision.criterion_id}: evidence line {end} "
                            f"exceeds {count}"
                        )
                        continue
        valid.append(evidence_id)

    if issues and decision.evidence_ids:
        decision = decision.model_copy(
            update={
                "status": CriterionStatus.NOT_EVALUATED.value,
                "evidence_ids": [],
                "reason": "evidence references failed validation",
                "reason_code": "INVALID_EVIDENCE_REFERENCE",
                "limitations": [*decision.limitations, *issues],
            }
        )
    else:
        decision = decision.model_copy(update={"evidence_ids": valid})
    return decision, issues


def _run_batch(
    *,
    client: LLMClient | None,
    model: str,
    criteria: list[EvaluationCriterionInput],
    context: EvidenceContext,
    batch_type: type[CriterionDecisionBatch] | type[ArchitectureDecisionBatch],
    prompt_version: str,
) -> DecisionBatch:
    started = datetime.now(UTC)
    if not criteria:
        return DecisionBatch(
            decisions=[],
            run=_metadata(
                started=started,
                duration=0.0,
                attempts=0,
                validation_status="SKIPPED",
                model=model,
                prompt_version=prompt_version,
            ),
        )
    if client is None:
        return DecisionBatch(
            decisions=_not_evaluated(
                criteria, "LLM_UNAVAILABLE", "no LLM client is configured"
            ),
            run=_metadata(
                started=started,
                duration=0.0,
                attempts=0,
                validation_status="FAILED",
                model=model,
                prompt_version=prompt_version,
                limitations=["LLM_UNAVAILABLE"],
            ),
        )

    messages = [
        {"role": "system", "content": _system_prompt()},
        {
            "role": "user",
            "content": (
                "Evaluate every criterion below and return JSON only.\n"
                f"Criteria: {_criteria_lines(criteria)}\n"
                f"Evidence: {_evidence_lines(context)}\n"
                "Allowed statuses: PASS, PARTIAL, FAIL, NOT_EVALUATED. "
                "Cite only evidence_ids from the supplied list."
            ),
        },
    ]
    pipeline = StructuredPipeline(
        client, max_attempts=MAX_ATTEMPTS, temperature=TEMPERATURE
    )
    try:
        output = pipeline.run(messages, batch_type, model=model)
    except LLMError as exc:
        code = (
            "LLM_INVALID_OUTPUT"
            if "structured output failed" in str(exc).lower()
            else "LLM_UNAVAILABLE"
        )
        return DecisionBatch(
            decisions=_not_evaluated(criteria, code, str(exc)),
            run=_metadata(
                started=started,
                duration=(datetime.now(UTC) - started).total_seconds(),
                attempts=pipeline.attempts_used,
                validation_status="FAILED",
                model=model,
                prompt_version=prompt_version,
                limitations=[code],
            ),
        )

    raw = (
        output.criteria
        if isinstance(output, CriterionDecisionBatch)
        else [*output.clean_architecture, *output.mvvm]
    )
    decisions, issues = _validate_decisions(raw, criteria, context)
    duration = (datetime.now(UTC) - started).total_seconds()
    return DecisionBatch(
        decisions=decisions,
        run=_metadata(
            started=started,
            duration=duration,
            attempts=pipeline.attempts_used,
            validation_status="VALIDATED" if not issues else "PARTIAL",
            model=model,
            prompt_version=prompt_version,
            limitations=issues,
        ),
    )


class LLMRequirementEvaluator:
    """Evaluates each declared acceptance criterion with the configured LLM."""

    def __init__(
        self,
        client: LLMClient | None,
        *,
        model: str = DEFAULT_MODEL,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.prompt_version = prompt_version

    def evaluate(
        self,
        criteria: list[EvaluationCriterionInput],
        context: EvidenceContext,
    ) -> DecisionBatch:
        return _run_batch(
            client=self.client,
            model=self.model,
            criteria=criteria,
            context=context,
            batch_type=CriterionDecisionBatch,
            prompt_version=self.prompt_version,
        )


class LLMArchitectureEvaluator:
    """Evaluates Clean Architecture and MVVM as independent matrices."""

    def __init__(
        self,
        client: LLMClient | None,
        *,
        model: str = DEFAULT_MODEL,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.prompt_version = prompt_version

    def criteria(self) -> list[EvaluationCriterionInput]:
        return [
            EvaluationCriterionInput(
                criterion_id=criterion_id,
                description=description,
                dimension="mvvm",
                subdimension="clean_architecture",
            )
            for criterion_id, description in CLEAN_ARCHITECTURE_CRITERIA
        ] + [
            EvaluationCriterionInput(
                criterion_id=criterion_id,
                description=description,
                dimension="mvvm",
                subdimension="mvvm",
            )
            for criterion_id, description in MVVM_CRITERIA
        ]

    def evaluate(self, context: EvidenceContext) -> DecisionBatch:
        return _run_batch(
            client=self.client,
            model=self.model,
            criteria=self.criteria(),
            context=context,
            batch_type=ArchitectureDecisionBatch,
            prompt_version=self.prompt_version,
        )


__all__ = [
    "ArchitectureDecisionBatch",
    "CriterionDecisionBatch",
    "DecisionBatch",
    "DEFAULT_MODEL",
    "EvaluationCriterionInput",
    "EvidenceValidationError",
    "LLMCriterionDecision",
    "LLMArchitectureEvaluator",
    "LLMRequirementEvaluator",
    "PROMPT_ID",
    "PROMPT_VERSION",
]
