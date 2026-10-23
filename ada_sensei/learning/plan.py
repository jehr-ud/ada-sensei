"""Deterministic learning-plan view (spec 008, RQ-LRN-025).

Builds the student's learning plan from the validated stage catalog and the
persisted learning profile: goal, full stage list in catalog order with the
current stage marked, current-stage objective/outcomes, and suggested next
activities. No LLM calls, no persistence writes, no stage advancement — pure
read-only rendering. With no topic, the `learn` action shows this plan; an
explicit topic keeps the existing AskAction teaching flow (router-owned).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanStage:
    number: int
    id: str
    title: str
    objective: str
    is_current: bool = False


@dataclass(frozen=True)
class LearningPlan:
    goal_title: str
    goal_description: str
    stages: list[PlanStage] = field(default_factory=list)
    current_stage_id: str | None = None
    current_objective: str | None = None
    current_outcomes: list[str] = field(default_factory=list)
    next_activities: list[str] = field(default_factory=list)
    locale: str = "en-US"
    catalog_id: str = ""
    catalog_version: str = ""


def build_learning_plan(catalog, profile, locale: str) -> LearningPlan:
    """Assemble the plan from catalog + profile without inventing facts.

    Unknown current stage (or none) yields a plan with no marked stage and no
    current-stage detail, never a guessed default.
    """
    loc = locale if locale in ("es-CO", "en-US") else "en-US"
    current_id = profile.current_stage_id if profile is not None else None
    known_ids = {s.id for s in catalog.stages}
    if current_id not in known_ids:
        current_id = None
    stages = [
        PlanStage(
            number=s.number,
            id=s.id,
            title=s.title,
            objective=s.objective,
            is_current=(s.id == current_id),
        )
        for s in catalog.stages
    ]
    current = next((s for s in catalog.stages if s.id == current_id), None)
    return LearningPlan(
        goal_title=catalog.title,
        goal_description=catalog.description,
        stages=stages,
        current_stage_id=current_id,
        current_objective=current.objective if current else None,
        current_outcomes=list(current.learning_outcomes) if current else [],
        next_activities=list(current.learning_activities) if current else [],
        locale=loc,
        catalog_id=catalog.catalog_id,
        catalog_version=catalog.catalog_version,
    )


def render_learning_plan(plan: LearningPlan) -> str:
    """Render the localized plan text with the current stage marked."""
    from ..locale.ui_strings import get_ui_string

    loc = plan.locale
    current_tag = get_ui_string("plan_current", loc)
    lines = [
        get_ui_string("plan_header", loc),
        "",
        f"{plan.goal_title}: {plan.goal_description}" if plan.goal_title else "",
        get_ui_string("onboard_stages", loc),
    ]
    for stage in plan.stages:
        marker = f"→ {stage.number}. {stage.title} ({stage.id}) [{current_tag}]"
        lines.append(marker if stage.is_current else f"  {stage.number}. {stage.title} ({stage.id})")
    lines.append("")
    if plan.current_stage_id is not None:
        objective = (plan.current_objective or "").strip()
        header = get_ui_string("plan_objective", loc)
        lines.append(f"{header} {objective}".rstrip())
        if plan.current_outcomes:
            lines.append(get_ui_string("plan_outcomes", loc))
            lines.extend(f"  - {outcome}" for outcome in plan.current_outcomes)
        if plan.next_activities:
            lines.append(get_ui_string("plan_next", loc))
            lines.extend(f"  - {activity}" for activity in plan.next_activities)
    else:
        lines.append(get_ui_string("stage_not_started", loc))
    return "\n".join(line for line in lines if line != "").strip() + "\n"


__all__ = ["LearningPlan", "PlanStage", "build_learning_plan", "render_learning_plan"]
