"""Deterministic next-action recommender (spec 0011 §§5, 8).

Pure function over an evidence-grounded :class:`TutorContext`. Priority order
mirrors the specification: blocking errors first, then evidenced difficulties,
outstanding requirements, reinforcement, comprehension checks, and next
objectives. Every candidate is validated against the action registry and
prerequisite rules — unsupported or unavailable actions are never returned.
Returns ``None`` when no useful recommendation can be justified instead of
inventing one. Never executes anything and never mutates stage or mastery.
"""

from __future__ import annotations

from ..cli.action_registry import check_availability, get_action
from .context import TutorContext
from .models import Recommendation


def _valid(ctx: TutorContext, action_id: str) -> bool:
    """Registry + prerequisite validation for a candidate recommendation."""
    if get_action(action_id) is None:
        return False
    available, _ = check_availability(
        action_id,
        project_path="/project" if ctx.project_active else None,
        exam_active=ctx.exam_active,
        locale=ctx.locale,
    )
    return available


def _stage_suffix(ctx: TutorContext) -> str:
    if ctx.stage_number is not None and ctx.stage_name:
        return f" (stage {ctx.stage_number}: {ctx.stage_name})"
    if ctx.stage_id:
        return f" (stage {ctx.stage_id})"
    return ""


def recommend_next(ctx: TutorContext) -> Recommendation | None:
    """Return at most one justified recommendation, or ``None``."""
    loc = ctx.locale

    # 1. Blocking error or missing prerequisite: help resolve it.
    if ctx.last_outcome == "error":
        if _valid(ctx, "help"):
            return Recommendation(
                action_id="help",
                rationale_es=(
                    "Ocurrió un error; revisa las acciones "
                    "disponibles y el siguiente paso."
                ),
                rationale_en=(
                    "Something failed; review the available "
                    "actions and next step."
                ),
                objective_es="Resolver el bloqueo actual.",
                objective_en="Resolve the current blocker.",
            )
        return None

    # 2. Evidenced learning difficulty: targeted practice.
    if ctx.mastery_gaps:
        if _valid(ctx, "practice"):
            gap = ctx.mastery_gaps[0]
            return Recommendation(
                action_id="practice",
                params={},
                rationale_es=f"Evidencia pendiente: {gap}."
                if loc == "es-CO"
                else f"Open evidence gap: {gap}.",
                rationale_en=f"Open evidence gap: {gap}.",
                objective_es="Reforzar el concepto con práctica adaptada.",
                objective_en="Reinforce the concept with adapted practice.",
            )
        return None

    # 3. Active exam: do not push; the student is mid-exam.
    if ctx.exam_active:
        return None

    # 4. After study interactions, reinforce through practice.
    if ctx.action_id in ("ask", "examples", "learn"):
        if _valid(ctx, "practice"):
            suffix = _stage_suffix(ctx)
            if loc == "es-CO":
                return Recommendation(
                    action_id="practice",
                    rationale_es=(
                        "Consolida lo aprendido con un ejercicio "
                        f"corto{suffix}."
                    ),
                    rationale_en="",
                    objective_es="Reforzar el concepto practicando.",
                    objective_en="",
                )
            return Recommendation(
                action_id="practice",
                rationale_en=(
                    "Consolidate what you learned with a short "
                    f"exercise{suffix}."
                ),
                rationale_es="",
                objective_en="Reinforce the concept through practice.",
                objective_es="",
            )
        return None

    # 5. After practice: check comprehension via assessment when a project
    #    exists, otherwise suggest examples to review the concept.
    if ctx.action_id == "practice":
        if ctx.project_active and _valid(ctx, "evaluate"):
            if loc == "es-CO":
                return Recommendation(
                    action_id="evaluate",
                    rationale_es=(
                        "Ya practicaste; verifica tu comprensión "
                        "con una evaluación."
                    ),
                    rationale_en="",
                    objective_es="Comprobar la comprensión de la etapa.",
                    objective_en="",
                    prerequisites_es="Requiere proyecto activo y tu confirmación.",
                    prerequisites_en="",
                )
            return Recommendation(
                action_id="evaluate",
                rationale_en=(
                    "You practiced; check your understanding "
                    "with an evaluation."
                ),
                rationale_es="",
                objective_en="Check stage comprehension.",
                objective_es="",
                prerequisites_en="Requires an active project and your confirmation.",
                prerequisites_es="",
            )
        if _valid(ctx, "learn"):
            if loc == "es-CO":
                return Recommendation(
                    action_id="learn",
                    rationale_es="Repasa los conceptos clave antes de la evaluación.",
                    rationale_en="",
                    objective_es="Consolidar la base de la etapa.",
                    objective_en="",
                )
            return Recommendation(
                action_id="learn",
                rationale_en="Review the key concepts before attempting an evaluation.",
                rationale_es="",
                objective_en="Consolidate the stage foundations.",
                objective_es="",
            )
        return None

    # 6. After an evaluation, route back to targeted practice.
    if ctx.action_id == "evaluate":
        if _valid(ctx, "practice"):
            if loc == "es-CO":
                return Recommendation(
                    action_id="practice",
                    rationale_es="Practica los criterios observados en la evaluación.",
                    rationale_en="",
                    objective_es="Reforzar los puntos detectados.",
                    objective_en="",
                )
            return Recommendation(
                action_id="practice",
                rationale_en="Practice the criteria observed in the evaluation.",
                rationale_es="",
                objective_en="Reinforce the detected points.",
                objective_es="",
            )
        return None

    # 7. After a diagnostic, study the recommended topics.
    if ctx.action_id == "diagnose":
        if _valid(ctx, "learn"):
            if loc == "es-CO":
                return Recommendation(
                    action_id="learn",
                    rationale_es="Estudia los temas señalados por el diagnóstico.",
                    rationale_en="",
                    objective_es="Abordar las brechas detectadas.",
                    objective_en="",
                )
            return Recommendation(
                action_id="learn",
                rationale_en="Study the topics flagged by the diagnostic.",
                rationale_es="",
                objective_en="Address the detected gaps.",
                objective_es="",
            )
        return None

    # No justified recommendation for meta actions (language/help) or unknown
    # contexts: the caller shows a neutral invite instead of inventing one.
    return None


__all__ = ["recommend_next"]
