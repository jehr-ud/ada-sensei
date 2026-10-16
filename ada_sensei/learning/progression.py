"""Deterministic progression policy engine (spec 008-learning-path). No LLM calls."""
from __future__ import annotations

from datetime import UTC, datetime

from ..urns import URN
from .models import (
    GateResult,
    MasteryAssessment,
    ProgressionDecision,
    ProgressionPolicy,
    StageRubric,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


class ProgressionPolicyEngine:
    """
    Evaluate all policy gates deterministically and produce a ProgressionDecision.

    Never calls the LLM. Never mutates evidence. All gate logic is pure Python
    arithmetic on the assessment and policy models.
    """

    def evaluate(
        self,
        assessment: MasteryAssessment,
        rubric: StageRubric,
        policy: ProgressionPolicy,
        next_stage_id: str | None,
    ) -> ProgressionDecision:
        gates: list[GateResult] = []
        reasons: list[str] = []
        has_insufficient_evidence = False

        gates_cfg = policy.decision_gates

        # -- Gate 1: evidence required for each dimension ------------------
        if gates_cfg.require_evidence_for_each_dimension:
            for dim_result in assessment.dimension_results:
                all_refs = [
                    r
                    for cr in dim_result.criterion_results
                    for r in cr.evidence_refs
                ] + list(dim_result.evidence_refs)
                if not all_refs:
                    gates.append(
                        GateResult(
                            gate="require_evidence_for_each_dimension",
                            passed=False,
                            reason=f"dimension {dim_result.dimension_id!r} has no evidence refs",
                        )
                    )
                    reasons.append(
                        f"No evidence found for dimension {dim_result.dimension_id!r}."
                    )
                    has_insufficient_evidence = True
            if not any(g.gate == "require_evidence_for_each_dimension" and not g.passed for g in gates):
                gates.append(
                    GateResult(
                        gate="require_evidence_for_each_dimension",
                        passed=True,
                        reason="all dimensions have at least one evidence ref",
                    )
                )

        # -- Gate 2: all required criteria assessed ------------------------
        if gates_cfg.require_all_rubric_criteria_assessed:
            unassessed: list[str] = []
            for dim in rubric.dimensions:
                assessed_ids = {cr.criterion_id for dim_r in assessment.dimension_results for cr in dim_r.criterion_results}
                for crit in dim.criteria:
                    if crit.required_for_decision and crit.id not in assessed_ids:
                        unassessed.append(crit.id)
            if unassessed:
                gates.append(
                    GateResult(
                        gate="require_all_rubric_criteria_assessed",
                        passed=False,
                        reason=f"unassessed required criteria: {unassessed}",
                    )
                )
                reasons.append(f"Required criteria not assessed: {unassessed}.")
                has_insufficient_evidence = True
            else:
                gates.append(
                    GateResult(
                        gate="require_all_rubric_criteria_assessed",
                        passed=True,
                        reason="all required criteria are assessed",
                    )
                )

        # -- Gate 3: exit challenge ----------------------------------------
        if gates_cfg.require_exit_challenge:
            passed = assessment.exit_challenge_completed
            gates.append(
                GateResult(
                    gate="require_exit_challenge",
                    passed=passed,
                    reason="exit challenge completed" if passed else "exit challenge not completed",
                )
            )
            if not passed:
                reasons.append("Exit challenge was not completed.")
                has_insufficient_evidence = True

        # -- Gate 4: comprehension check -----------------------------------
        if gates_cfg.require_comprehension_check:
            passed = assessment.comprehension_check_completed
            gates.append(
                GateResult(
                    gate="require_comprehension_check",
                    passed=passed,
                    reason="comprehension check completed" if passed else "comprehension check not completed",
                )
            )
            if not passed:
                reasons.append("Comprehension check was not completed.")
                has_insufficient_evidence = True

        # If any evidence gate failed, status is INSUFFICIENT_EVIDENCE
        if has_insufficient_evidence:
            return ProgressionDecision(
                decision_id=URN.make("decision"),
                student_id=assessment.student_id,
                from_stage_id=assessment.stage_id,
                to_stage_id=None,
                status="INSUFFICIENT_EVIDENCE",
                gate_results=gates,
                reasons=reasons,
                recommended_activity="Complete all required evidence before requesting a progression decision.",
                policy_id=assessment.policy_id,
                policy_version=assessment.policy_version,
                assessment_id=assessment.id,
                created_at=_now(),
            )

        # -- Gate 5: critical criterion minimum scores --------------------
        crit_map: dict[str, float | None] = {}
        for dim_result in assessment.dimension_results:
            for cr in dim_result.criterion_results:
                crit_map[cr.criterion_id] = cr.score

        critical_passed = True
        for dim in rubric.dimensions:
            for crit in dim.criteria:
                if crit.critical:
                    score = crit_map.get(crit.id)
                    if score is None:
                        gates.append(
                            GateResult(
                                gate="minimum_critical_criterion_score",
                                passed=False,
                                reason=f"critical criterion {crit.id!r} has no score",
                            )
                        )
                        reasons.append(f"Critical criterion {crit.id!r} was not evaluated.")
                        critical_passed = False
                    elif score < gates_cfg.minimum_critical_criterion_score:
                        gates.append(
                            GateResult(
                                gate="minimum_critical_criterion_score",
                                passed=False,
                                reason=(
                                    f"critical criterion {crit.id!r} scored {score:.2f}, "
                                    f"need >= {gates_cfg.minimum_critical_criterion_score}"
                                ),
                            )
                        )
                        reasons.append(
                            f"Critical criterion {crit.id!r} below threshold "
                            f"({score:.2f} < {gates_cfg.minimum_critical_criterion_score})."
                        )
                        critical_passed = False

        if critical_passed:
            gates.append(
                GateResult(
                    gate="minimum_critical_criterion_score",
                    passed=True,
                    reason="all critical criteria meet the minimum score",
                )
            )

        # -- Gate 6: minimum dimension scores -----------------------------
        dim_scores: dict[str, float | None] = {
            dr.dimension_id: dr.score for dr in assessment.dimension_results
        }
        dim_passed = True
        for dim_id, dim_score in dim_scores.items():
            if dim_score is None:
                gates.append(
                    GateResult(
                        gate="minimum_each_dimension_score",
                        passed=False,
                        reason=f"dimension {dim_id!r} has no score",
                    )
                )
                reasons.append(f"Dimension {dim_id!r} could not be scored.")
                dim_passed = False
            elif dim_score < gates_cfg.minimum_each_dimension_score:
                gates.append(
                    GateResult(
                        gate="minimum_each_dimension_score",
                        passed=False,
                        reason=(
                            f"dimension {dim_id!r} scored {dim_score:.2f}, "
                            f"need >= {gates_cfg.minimum_each_dimension_score}"
                        ),
                    )
                )
                reasons.append(
                    f"Dimension {dim_id!r} below threshold "
                    f"({dim_score:.2f} < {gates_cfg.minimum_each_dimension_score})."
                )
                dim_passed = False

        if dim_passed:
            gates.append(
                GateResult(
                    gate="minimum_each_dimension_score",
                    passed=True,
                    reason="all dimension scores meet the minimum",
                )
            )

        # -- Gate 7: minimum overall score --------------------------------
        overall = assessment.overall_score
        if overall is None:
            gates.append(
                GateResult(
                    gate="minimum_overall_score",
                    passed=False,
                    reason="overall score is not available",
                )
            )
            reasons.append("Overall score could not be computed.")
            overall_passed = False
        elif overall < gates_cfg.minimum_overall_score:
            gates.append(
                GateResult(
                    gate="minimum_overall_score",
                    passed=False,
                    reason=(
                        f"overall score {overall:.2f} < {gates_cfg.minimum_overall_score}"
                    ),
                )
            )
            reasons.append(
                f"Overall score below threshold ({overall:.2f} < {gates_cfg.minimum_overall_score})."
            )
        else:
            gates.append(
                GateResult(
                    gate="minimum_overall_score",
                    passed=True,
                    reason=f"overall score {overall:.2f} >= {gates_cfg.minimum_overall_score}",
                )
            )

        # -- Final decision -----------------------------------------------
        all_passed = all(g.passed for g in gates)
        if all_passed:
            return ProgressionDecision(
                decision_id=URN.make("decision"),
                student_id=assessment.student_id,
                from_stage_id=assessment.stage_id,
                to_stage_id=next_stage_id,
                status="READY",
                gate_results=gates,
                reasons=["All gates passed. Student is ready to advance."],
                recommended_activity=(
                    f"Advance to stage {next_stage_id!r}." if next_stage_id else "All stages complete."
                ),
                policy_id=assessment.policy_id,
                policy_version=assessment.policy_version,
                assessment_id=assessment.id,
                created_at=_now(),
            )

        return ProgressionDecision(
            decision_id=URN.make("decision"),
            student_id=assessment.student_id,
            from_stage_id=assessment.stage_id,
            to_stage_id=None,
            status="NOT_READY",
            gate_results=gates,
            reasons=reasons,
            recommended_activity=(
                "Review the failed criteria and practice the corresponding concepts "
                "before requesting a new assessment."
            ),
            policy_id=assessment.policy_id,
            policy_version=assessment.policy_version,
            assessment_id=assessment.id,
            created_at=_now(),
        )


__all__ = ["ProgressionPolicyEngine"]
