"""Deterministic evaluation report assembly for the exam workflow."""

from __future__ import annotations

from typing import Any

from ..models import Evidence, NotEvaluatedReason
from ..toolchain.models import HealthCheckStatus, ToolchainPreparationResult, ToolStatus
from ..urns import URN
from .llm_evaluators import LLMCriterionDecision
from .models import (
    NON_EVALUABLE_STATUSES,
    AnalyzerCoverage,
    ArchitectureSubdimension,
    CalculationTraceStep,
    CoverageSummary,
    CriterionResult,
    CriterionStatus,
    DimensionResult,
    EvaluationReport,
    EvidenceReference,
    Finding,
    Limitation,
    LLMRunMetadata,
    Observation,
    OverallStatus,
    PriorityAction,
    RequirementResult,
    TestSummary,
    ToolRun,
)
from .rubric import UNIFIED_RUBRIC

ANALYZER_VERSION = "v1"
RULESET_VERSION = "unified-android:v1"

_DIMENSION_ANALYZERS: dict[str, tuple[str, ...]] = {
    "functional_requirements": ("requirement_matcher",),
    "tests": ("unit_test_reports", "requirement_test_links"),
    "code_quality": ("detekt", "android_lint", "ktlint"),
    "mvvm": ("mvvm_static_analyzer",),
    "android_practices": ("android_static_analyzer",),
}

_TOOL_EVIDENCE_SOURCES = {
    "detekt": "detekt",
    "android_lint": "android_lint",
    "ktlint": "ktlint",
    "gradle": "gradle",
    "test": "test",
}

_NON_EVALUABLE_REASONS = {
    NotEvaluatedReason.no_evidence.value,
    NotEvaluatedReason.tool_unavailable.value,
    NotEvaluatedReason.build_failed.value,
    NotEvaluatedReason.no_exercise.value,
    NotEvaluatedReason.no_limit.value,
    NotEvaluatedReason.ungrounded_claim.value,
}


LLM_STATUS_TO_SCORE_5 = {
    "PASS": 5.0,
    "PARTIAL": 2.5,
    "FAIL": 0.0,
}


class EvaluatorAgent:
    """Builds the official typed report from deterministic evidence only.

    The agent never calls an LLM and never changes a score. It projects the
    already-computed exam result into the structured contract consumed by
    presentation and by the PDF renderer.
    """

    def build_report(
        self,
        *,
        result: Any,
        definition: Any,
        evidence: Any,
        build_failed: bool = False,
        tool_runs: list[ToolRun] | None = None,
        toolchain_preparation: ToolchainPreparationResult | None = None,
        requirement_decisions: dict[str, LLMCriterionDecision] | None = None,
        architecture_decisions: dict[str, LLMCriterionDecision] | None = None,
        llm_runs: list[LLMRunMetadata] | None = None,
        rubric_definition: Any | None = None,
    ) -> EvaluationReport:
        rubric = rubric_definition or UNIFIED_RUBRIC
        calculation = result.score_calculation
        lines = list(calculation.lines) if calculation is not None else []
        score_by_dimension = {line.dimension: line.score for line in lines}
        reason_by_dimension = {
            line.dimension: (
                line.not_evaluated_reason.value
                if line.not_evaluated_reason is not None
                else None
            )
            for line in lines
        }
        weight_by_dimension = {line.dimension: line.weight for line in lines}

        evidence_references = [
            self._evidence_reference(item) for item in getattr(evidence, "evidence", [])
        ]
        findings = self._findings(evidence_references)
        criterion_results = self._criterion_results(
            result,
            definition,
            weight_by_dimension,
            score_by_dimension,
            reason_by_dimension,
            rubric,
            requirement_decisions,
            architecture_decisions,
        )
        dimension_results = self._dimension_results(
            criterion_results,
            lines,
            weight_by_dimension,
            reason_by_dimension,
            rubric,
        )
        architecture_results = self._architecture_subdimensions(
            criterion_results, rubric
        )
        requirement_results = self._requirement_results(
            result, definition, requirement_decisions
        )
        test_summary = self._test_summary(
            result, definition, requirement_results, criterion_results
        )
        coverage = self._analyzer_coverage(
            criterion_results, getattr(evidence, "evidence", []), rubric
        )
        coverage_summary = self._coverage_summary(calculation, criterion_results)
        limitations = self._limitations(result, lines, build_failed)
        if coverage_summary is not None and coverage_summary.partial:
            limitations.append(
                Limitation(
                    limitation_id="limitation://coverage",
                    dimension="global",
                    reason_code="partial_evaluation_coverage",
                    description="evaluation coverage is partial",
                    coverage_impact=(
                        f"excluded weight {coverage_summary.excluded_weight:.4f}"
                    ),
                    required_action="supply the missing evidence and rerun the exam",
                )
            )
        if toolchain_preparation is not None:
            limitations.extend(self._toolchain_limitations(toolchain_preparation))
        trace = self._trace(dimension_results)
        infrastructure_failed = (
            toolchain_preparation is not None and not toolchain_preparation.ready
        )
        blocked = build_failed or any(
            reason
            in {
                NotEvaluatedReason.build_failed.value,
                NotEvaluatedReason.tool_unavailable.value,
            }
            for reason in reason_by_dimension.values()
            if reason is not None
        ) or any(
            item.reason_code
            in {"LLM_UNAVAILABLE", "LLM_INVALID_OUTPUT", "EXECUTION_ERROR"}
            for item in criterion_results
        ) or any(
            run.validation_status == "FAILED"
            and "LLM_UNAVAILABLE" in run.limitations
            for run in (llm_runs or [])
        )
        complete = (
            bool(dimension_results)
            and all(dimension.score is not None for dimension in dimension_results)
            and not any(
                item.status in NON_EVALUABLE_STATUSES for item in criterion_results
            )
        )
        if infrastructure_failed:
            status = OverallStatus.INCOMPLETE_INFRASTRUCTURE
        elif blocked:
            status = OverallStatus.BLOCKED
        elif complete:
            status = OverallStatus.COMPLETE
        else:
            status = OverallStatus.PARTIAL
        scores = self._overall_scores(dimension_results, status, result)
        priority_actions = self._priority_actions(criterion_results, limitations)
        strengths = self._strengths(criterion_results)

        return EvaluationReport(
            report_id=result.report_id or URN.make("evaluation_report"),
            student_id=getattr(result, "student_id", "") or "",
            project_id=getattr(result, "project_id", "") or "",
            exam_id=getattr(result, "exam_id", "") or "",
            attempt_id=getattr(result, "attempt_id", "")
            or getattr(result, "exam_attempt_id", "")
            or "",
            locale=getattr(result, "locale", None) or "en-US",
            rubric_id=getattr(result, "rubric_id", None) or rubric.id,
            rubric_version=getattr(result, "rubric_version", None) or rubric.version,
            overall_status=status,
            overall_score_5=scores[0],
            overall_score_50=scores[1],
            suggested_grade=scores[2],
            dimension_results=dimension_results,
            criterion_results=criterion_results,
            requirement_results=requirement_results,
            test_summary=test_summary,
            tool_runs=tool_runs
            or self._tool_runs(
                getattr(evidence, "evidence", []), toolchain_preparation
            ),
            findings=findings,
            evidence=evidence_references,
            analyzer_coverage=coverage,
            limitations=limitations,
            calculation_trace=trace,
            observations=self._observations(findings),
            ruleset_versions={
                "rubric": getattr(result, "rubric_ref", None) or rubric.ref,
                "analyzers": ANALYZER_VERSION,
            },
            toolchain_manifest=(
                toolchain_preparation.manifest
                if toolchain_preparation is not None
                else None
            ),
            toolchain_evidence=(
                list(toolchain_preparation.executions)
                if toolchain_preparation is not None
                else []
            ),
            llm_runs=list(llm_runs or []),
            architecture_results=architecture_results,
            coverage_summary=coverage_summary,
            priority_actions=priority_actions,
            strengths=strengths,
            supersedes_report_id=getattr(result, "supersedes_report_id", None),
        )

    @staticmethod
    def _to_score_5(score: float | int | None) -> float | None:
        if score is None:
            return None
        return round(float(score) / 4.0 * 5.0, 2)

    @staticmethod
    def _status(score: float | None) -> CriterionStatus:
        if score is None:
            return CriterionStatus.NOT_EVALUATED
        if score >= 4.5:
            return CriterionStatus.PASS
        if score >= 2.5:
            return CriterionStatus.PARTIAL
        return CriterionStatus.FAIL

    @staticmethod
    def _evidence_reference(item: Evidence) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=item.id or URN.make("evidence"),
            type=item.type,
            path=item.file,
            line=item.line,
            line_start=item.line_start if item.line_start is not None else item.line,
            line_end=item.line_end if item.line_end is not None else item.line,
            symbol=item.symbol,
            excerpt=item.excerpt[:240],
            content_hash=item.content_hash,
            collector=item.collector,
            reliability=item.reliability,
            tool=item.source,
            command=item.command,
            summary=item.message,
        )

    def _findings(self, evidence: list[EvidenceReference]) -> list[Finding]:
        findings: list[Finding] = []
        for item in evidence:
            severity = (item.type or "").lower()
            if severity not in {"error", "warning", "info"}:
                continue
            findings.append(
                Finding(
                    finding_id=f"finding://{item.evidence_id}",
                    rule_id=f"rule://{item.type}",
                    severity=severity,
                    message=item.summary,
                    dimension="code_quality",
                    evidence_ids=[item.evidence_id],
                    recommendation_code=f"review_{item.type}",
                )
            )
        return findings

    def _criterion_results(
        self,
        result: Any,
        definition: Any,
        weights: dict[str, float],
        scores: dict[str, float | None],
        reasons: dict[str, str | None],
        rubric: Any,
        requirement_decisions: dict[str, LLMCriterionDecision] | None = None,
        architecture_decisions: dict[str, LLMCriterionDecision] | None = None,
    ) -> list[CriterionResult]:
        criteria: list[CriterionResult] = []
        for item in getattr(result, "criteria", []):
            score = self._to_score_5(item.score)
            criteria.append(
                CriterionResult(
                    criterion_id=item.requirement_id or URN.make("criterion"),
                    dimension=item.dimension,
                    status=self._status(score),
                    score=score,
                    weight=item.weight,
                    weighted_score=(
                        round(score * item.weight, 4) if score is not None else None
                    ),
                    evidence_ids=list(item.evidence_refs),
                    reason_code=(
                        item.not_evaluated_reason.value
                        if item.not_evaluated_reason is not None
                        else None
                    ),
                    analyzer="requirement_matcher",
                    analyzer_version=ANALYZER_VERSION,
                    rule_version=rubric.ref,
                )
            )
        for dimension in rubric.dimensions:
            if dimension.id == "functional_requirements":
                continue
            if dimension.id == "mvvm" and architecture_decisions is not None:
                continue
            dimension_score = self._to_score_5(scores.get(dimension.id))
            reason = reasons.get(dimension.id)
            for subcriterion in dimension.subcriteria:
                criterion_score = None if reason else dimension_score
                criteria.append(
                    CriterionResult(
                        criterion_id=subcriterion.id,
                        dimension=dimension.id,
                        status=self._status(criterion_score),
                        score=criterion_score,
                        weight=subcriterion.weight,
                        weighted_score=(
                            round(criterion_score * subcriterion.weight, 4)
                            if criterion_score is not None
                            else None
                        ),
                        reason_code=reason,
                        analyzer=_DIMENSION_ANALYZERS[dimension.id][0],
                        analyzer_version=ANALYZER_VERSION,
                        rule_version=rubric.ref,
                    )
                )
        if requirement_decisions is not None:
            for requirement in getattr(definition, "requirements", []):
                acceptance = list(requirement.acceptance_criteria)
                if not acceptance:
                    acceptance = [requirement]
                weight = requirement.weight / len(acceptance)
                for item in acceptance:
                    item_id = getattr(item, "id", None) or requirement.requirement_id
                    decision = requirement_decisions.get(item_id)
                    if decision is not None:
                        criteria.append(
                            self._llm_criterion(
                                decision,
                                dimension="functional_requirements",
                                weight=weight,
                                requirement_id=requirement.requirement_id,
                                subdimension=None,
                                rubric=rubric,
                            )
                        )
        if architecture_decisions is not None:
            subweights = {
                item.id: item.weight for item in rubric.dimension("mvvm").subcriteria
            }
            for criterion_id, decision in architecture_decisions.items():
                subdimension = (
                    "clean_architecture" if criterion_id.startswith("C") else "mvvm"
                )
                criteria.append(
                    self._llm_criterion(
                        decision,
                        dimension="mvvm",
                        weight=subweights.get(criterion_id, 0.0),
                        requirement_id=None,
                        subdimension=subdimension,
                        rubric=rubric,
                    )
                )
        return criteria

    @staticmethod
    def _llm_criterion(
        decision: LLMCriterionDecision,
        *,
        dimension: str,
        weight: float,
        requirement_id: str | None,
        subdimension: str | None,
        rubric: Any,
    ) -> CriterionResult:
        status = CriterionStatus(decision.status)
        score = (
            LLM_STATUS_TO_SCORE_5.get(decision.status)
            if status not in NON_EVALUABLE_STATUSES
            else None
        )
        return CriterionResult(
            criterion_id=decision.criterion_id,
            dimension=dimension,
            status=status,
            score=score,
            weight=weight,
            weighted_score=round(score * weight, 4) if score is not None else None,
            evidence_ids=list(decision.evidence_ids),
            reason_code=decision.reason_code or (
                None if score is not None else status.value
            ),
            analyzer="llm_criterion_evaluator",
            analyzer_version=ANALYZER_VERSION,
            rule_version=rubric.ref,
            requirement_id=requirement_id,
            subdimension=subdimension,
            reason=decision.reason,
            confidence=decision.confidence,
            limitations=list(decision.limitations),
            recommended_action=decision.recommended_action,
            score_source="llm_status",
        )

    def _dimension_results(
        self,
        criteria: list[CriterionResult],
        lines: list[Any],
        weights: dict[str, float],
        reasons: dict[str, str | None],
        rubric: Any,
    ) -> list[DimensionResult]:
        results: list[DimensionResult] = []
        for line in lines:
            dimension = rubric.dimension(line.dimension)
            own_criteria = [c for c in criteria if c.dimension == line.dimension]
            covered = sum(1 for c in own_criteria if c.score is not None)
            score = self._to_score_5(line.score)
            results.append(
                DimensionResult(
                    dimension_id=line.dimension,
                    name=dimension.description or line.dimension,
                    weight=weights.get(line.dimension, dimension.weight),
                    score=score,
                    weighted_contribution=(
                        round(score * weights.get(line.dimension, dimension.weight), 4)
                        if score is not None
                        else None
                    ),
                    status=self._status(score),
                    coverage=(covered / len(own_criteria)) if own_criteria else 0.0,
                    reason_code=reasons.get(line.dimension),
                    criteria=own_criteria,
                )
            )
        return results

    @staticmethod
    def _architecture_subdimensions(
        criteria: list[CriterionResult], rubric: Any
    ) -> list[ArchitectureSubdimension]:
        subcriteria = {
            item.id: item.weight for item in rubric.dimension("mvvm").subcriteria
        }
        outputs: list[ArchitectureSubdimension] = []
        for name in ("clean_architecture", "mvvm"):
            own = [
                item
                for item in criteria
                if item.dimension == "mvvm" and item.subdimension == name
            ]
            if not own:
                continue
            total = sum(subcriteria.get(item.criterion_id, item.weight) for item in own)
            evaluated = [item for item in own if item.score is not None]
            weighted = sum(
                item.score * subcriteria.get(item.criterion_id, item.weight)
                for item in evaluated
            )
            score = weighted / total if total else None
            coverage = sum(
                subcriteria.get(item.criterion_id, item.weight) for item in evaluated
            ) / total if total else 0.0
            status = (
                EvaluatorAgent._status(score)
                if evaluated
                else CriterionStatus.NOT_EVALUATED
            )
            if any(item.status is CriterionStatus.FAIL for item in own):
                status = CriterionStatus.FAIL
            outputs.append(
                ArchitectureSubdimension(
                    name=name,
                    weight_in_d4=0.5,
                    score_5=score,
                    coverage=round(coverage, 4),
                    status=status,
                    criteria=own,
                )
            )
        return outputs

    @staticmethod
    def _coverage_summary(
        calculation: Any, criteria: list[CriterionResult]
    ) -> CoverageSummary | None:
        if calculation is None:
            return None
        evaluated = sum(
            1 for item in criteria if item.status not in NON_EVALUABLE_STATUSES
        )
        evaluated_weight = float(getattr(calculation, "evaluated_weight", 1.0))
        excluded_weight = float(getattr(calculation, "excluded_weight", 0.0))
        return CoverageSummary(
            evaluated_weight=round(evaluated_weight, 6),
            excluded_weight=round(excluded_weight, 6),
            evaluated_criteria=evaluated,
            total_criteria=len(criteria),
            partial=excluded_weight > 1e-6 or evaluated < len(criteria),
        )

    @staticmethod
    def _priority_actions(
        criteria: list[CriterionResult], limitations: list[Limitation]
    ) -> list[PriorityAction]:
        actions: list[PriorityAction] = [
            PriorityAction(
                action_id=f"action://{item.criterion_id}",
                target_id=item.criterion_id,
                text=item.recommended_action,
                impact=f"{item.dimension}: {item.status.value}",
            )
            for item in criteria
            if item.recommended_action
            and item.status in {CriterionStatus.FAIL, CriterionStatus.PARTIAL}
        ]
        if not actions:
            actions = [
                PriorityAction(
                    action_id=item.limitation_id,
                    target_id=item.dimension,
                    text=item.required_action,
                    impact=item.coverage_impact,
                )
                for item in limitations
            ]
        return actions[:5]

    @staticmethod
    def _strengths(criteria: list[CriterionResult]) -> list[str]:
        values: list[str] = []
        for item in criteria:
            if item.status is not CriterionStatus.PASS or not item.reason:
                continue
            text = f"{item.criterion_id}: {item.reason}"
            if text not in values:
                values.append(text)
            if len(values) == 5:
                break
        return values

    @staticmethod
    def _requirement_results(
        result: Any,
        definition: Any,
        decisions: dict[str, LLMCriterionDecision] | None = None,
    ) -> list[RequirementResult]:
        by_id = {
            item.requirement_id: item
            for item in getattr(result, "criteria", [])
            if item.requirement_id
        }
        evidence_by_id = {
            item.id: item for item in getattr(result, "evidence", []) if item.id
        }
        outputs: list[RequirementResult] = []
        for requirement in getattr(definition, "requirements", []):
            matched: list[str] = []
            files: list[str] = []
            passed_cases = 0
            total_cases = 0
            criterion = by_id.get(requirement.requirement_id)
            if decisions is not None:
                criteria_ids = [item.id for item in requirement.acceptance_criteria]
                if not criteria_ids:
                    criteria_ids = [requirement.requirement_id]
                children = [
                    decisions[item_id]
                    for item_id in criteria_ids
                    if item_id in decisions
                ]
                values = [
                    LLM_STATUS_TO_SCORE_5[item.status]
                    for item in children
                    if item.status in LLM_STATUS_TO_SCORE_5
                ]
                score = sum(values) / len(values) if values else None
                matched = list(
                    dict.fromkeys(
                        item
                        for child in children
                        for item in child.evidence_ids
                    )
                )
                passed_cases = sum(
                    1 for item in children if item.status == CriterionStatus.PASS
                )
                total_cases = len(children)
            else:
                score = (
                    EvaluatorAgent._to_score_5(criterion.score) if criterion else None
                )
                matched = list(criterion.evidence_refs) if criterion else []
                files = [
                    item.file for item in criterion.evidence if item.file
                ] if criterion else []
            for evidence_id in matched:
                item = evidence_by_id.get(evidence_id)
                if item is None or not item.file:
                    continue
                start = item.line_start if item.line_start is not None else item.line
                end = item.line_end if item.line_end is not None else item.line
                suffix = (
                    f":{start}-{end}"
                    if start is not None and end is not None
                    else ""
                )
                files.append(f"{item.file}{suffix}")
            outputs.append(
                RequirementResult(
                    requirement_id=requirement.requirement_id,
                    title=requirement.title,
                    description=requirement.description,
                    functional_weight=requirement.weight,
                    status=EvaluatorAgent._status(score),
                    score=score,
                    passed_cases=passed_cases,
                    total_cases=total_cases,
                    evidence_ids=matched,
                    files_lines=list(dict.fromkeys(files)),
                )
            )
        return outputs

    @staticmethod
    def _test_summary(
        result: Any,
        definition: Any,
        requirements: list[RequirementResult],
        criteria: list[CriterionResult],
    ) -> TestSummary:
        unit_tests = [
            item
            for item in getattr(result, "evidence", [])
            if item.type in {"unit_test", "test"}
        ]
        passed = sum(1 for item in unit_tests if item.status == "pass")
        failed = sum(1 for item in unit_tests if item.status == "fail")
        skipped = sum(1 for item in unit_tests if item.status == "skip")
        errors = sum(1 for item in unit_tests if item.status == "error")
        functional = [
            requirement
            for requirement in getattr(definition, "requirements", [])
            if requirement.dimension == "functional_requirements"
        ]
        functional_ids = {item.requirement_id for item in functional}
        covered = sum(
            1
            for item in requirements
            if item.requirement_id in functional_ids and item.score is not None
        )
        total = len(functional)
        ratio = covered / total if total else 0.0
        t1 = min(5.0, ratio / 0.8 * 5.0) if total else None
        denominator = passed + failed
        t2 = round(passed / denominator * 5.0, 2) if denominator else None
        t3 = next(
            (item.score for item in criteria if item.criterion_id == "T3"), None
        )
        return TestSummary(
            executed=len(unit_tests),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            covered_requirements=covered,
            total_requirements=total,
            coverage_ratio=round(ratio, 4),
            coverage_threshold=0.8,
            threshold_met=ratio >= 0.8,
            t1_score=round(t1, 2) if t1 is not None else None,
            t2_score=t2,
            t3_score=t3,
        )

    def _analyzer_coverage(
        self,
        criteria: list[CriterionResult],
        evidence: list[Evidence],
        rubric: Any,
    ) -> list[AnalyzerCoverage]:
        evidence_sources = {item.source for item in evidence}
        coverage: list[AnalyzerCoverage] = []
        for dimension in rubric.dimensions:
            required = _DIMENSION_ANALYZERS[dimension.id]
            executed = [name for name in required if name in evidence_sources]
            missing = [name for name in required if name not in evidence_sources]
            own = [item for item in criteria if item.dimension == dimension.id]
            coverage.append(
                AnalyzerCoverage(
                    dimension=dimension.id,
                    required_analyzers=list(required),
                    executed_analyzers=executed,
                    not_configured=missing,
                    covered_criteria=[
                        item.criterion_id for item in own if item.score is not None
                    ],
                )
            )
        return coverage

    def _limitations(
        self, result: Any, lines: list[Any], build_failed: bool
    ) -> list[Limitation]:
        limitations: list[Limitation] = []
        for index, text in enumerate(getattr(result, "limitations", []), start=1):
            limitations.append(
                Limitation(
                    limitation_id=f"limitation://{index}",
                    dimension="global",
                    reason_code="evidence_limitation",
                    description=text,
                    coverage_impact="recorded",
                    required_action="review the named evidence gap",
                )
            )
        for line in lines:
            if line.not_evaluated_reason is None:
                continue
            limitations.append(
                Limitation(
                    limitation_id=f"limitation://{line.dimension}",
                    dimension=line.dimension,
                    reason_code=line.not_evaluated_reason.value,
                    description=f"{line.dimension} was not evaluated",
                    coverage_impact=f"excluded weight {line.weight:.2f}",
                    required_action=(
                        "run the missing analyzer or supply the missing evidence"
                    ),
                    analyzer_version=ANALYZER_VERSION,
                    rule_version=RULESET_VERSION,
                )
            )
        if build_failed:
            limitations.append(
                Limitation(
                    limitation_id="limitation://build",
                    dimension="global",
                    reason_code=NotEvaluatedReason.build_failed.value,
                    description="the build did not complete",
                    coverage_impact=(
                        "compilation-dependent dimensions are not evaluated"
                    ),
                    required_action="fix the build and rerun the evaluation",
                )
            )
        return limitations

    @staticmethod
    def _trace(dimensions: list[DimensionResult]) -> list[CalculationTraceStep]:
        steps: list[CalculationTraceStep] = [
            CalculationTraceStep(
                step_id="trace://dimensions",
                rule_id="rule://unified-dimensions",
                inputs={"dimensions": len(dimensions)},
                operation="collect dimension scores on the 0-5 scale",
            )
        ]
        for dimension in dimensions:
            steps.append(
                CalculationTraceStep(
                    step_id=f"trace://{dimension.dimension_id}",
                    rule_id=f"rule://{dimension.dimension_id}",
                    inputs={
                        "score": dimension.score,
                        "weight": dimension.weight,
                    },
                    operation="score * weight",
                    output=dimension.weighted_contribution,
                )
            )
        return steps

    @staticmethod
    def _observations(findings: list[Finding]) -> list[Observation]:
        return [
            Observation(
                observation_id=f"observation://{finding.finding_id}",
                trigger_rule_id=finding.rule_id,
                severity=finding.severity,
                message_template_id=f"template://{finding.recommendation_code}",
                message=finding.message,
                evidence_ids=list(finding.evidence_ids),
                finding_ids=[finding.finding_id],
            )
            for finding in findings
        ]

    @staticmethod
    def _toolchain_limitations(
        preparation: ToolchainPreparationResult,
    ) -> list[Limitation]:
        limitations: list[Limitation] = []
        for index, blocker in enumerate(preparation.blockers, start=1):
            limitations.append(
                Limitation(
                    limitation_id=f"limitation://toolchain-{index}",
                    dimension="code_quality",
                    tool_state=ToolStatus.NOT_CONFIGURED.value,
                    reason_code="toolchain_preparation_failed",
                    description=blocker,
                    coverage_impact="D3 cannot be completed",
                    required_action="resolve the toolchain blocker and rerun",
                    analyzer_version=ANALYZER_VERSION,
                    rule_version=RULESET_VERSION,
                )
            )
        return limitations

    @staticmethod
    def _tool_runs(
        evidence: list[Evidence],
        preparation: ToolchainPreparationResult | None = None,
    ) -> list[ToolRun]:
        if preparation is not None:
            runs: list[ToolRun] = []
            for item in preparation.executions:
                execution_status = (
                    ToolStatus.READY.value
                    if item.status is ToolStatus.READY
                    and item.health_check.status is HealthCheckStatus.PASS
                    else item.status.value
                )
                duration = None
                if item.started_at is not None and item.finished_at is not None:
                    duration = round(
                        (item.finished_at - item.started_at).total_seconds(), 3
                    )
                runs.append(
                    ToolRun(
                        tool_id=item.tool_id.value,
                        name=item.tool_id.value,
                        preparation_status=item.status.value,
                        execution_status=execution_status,
                        version=item.version,
                        command=" ".join(item.command) or None,
                        task=item.task,
                        duration_seconds=duration,
                        output_artifact=(
                            item.report_paths[0] if item.report_paths else None
                        ),
                        limitation=item.error_cause or item.health_check.reason or None,
                    )
                )
            return runs
        runs = []
        for tool_id, source in _TOOL_EVIDENCE_SOURCES.items():
            items = [item for item in evidence if item.source == source]
            execution = "READY" if items else "NOT_CONFIGURED"
            runs.append(
                ToolRun(
                    tool_id=tool_id,
                    name=tool_id,
                    preparation_status=execution,
                    execution_status=execution,
                )
            )
        return runs

    @staticmethod
    def _overall_scores(
        dimensions: list[DimensionResult], status: OverallStatus, result: Any
    ) -> tuple[float | None, int | None, float | None]:
        if status is OverallStatus.INCOMPLETE_INFRASTRUCTURE:
            return None, None, None
        score_50 = getattr(result, "raw_score_50", None)
        score_5 = getattr(result, "overall_score", None)
        if score_50 is not None:
            score_5 = round(float(score_50) / 10.0, 2)
        elif score_5 is None:
            contributions = [
                item.weighted_contribution
                for item in dimensions
                if item.weighted_contribution is not None
            ]
            if not contributions:
                return None, None, None
            score_5 = round(sum(contributions), 2)
        if score_50 is None:
            score_50 = int(round(float(score_5) * 10))
        if status is OverallStatus.COMPLETE and score_50 is None:
            return None, None, None
        suggested = getattr(result, "suggested_grade", None)
        if suggested is None:
            suggested = round(1.0 + (float(score_5) / 5.0) * 4.0, 1)
        return float(score_5), int(score_50), suggested


__all__ = ["EvaluatorAgent"]
