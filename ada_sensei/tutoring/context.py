"""Evidence-grounded tutoring context (spec 0011 §4).

:func:`assemble_context` collects only available, persisted facts: current
stage (+ objective from the locale catalog), selected action, locale, project
and exam state, last outcome, and planner-reported gaps. Anything unavailable
stays ``None`` — the system distinguishes missing information from negative
results and never invents preferences, history, mastery, evidence, or project
facts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorContext:
    """Read-only snapshot used for stage-aware responses and recommendations."""

    student_id: str | None = None
    stage_id: str | None = None
    stage_number: int | None = None
    stage_name: str | None = None
    stage_objective: str | None = None
    action_id: str | None = None
    locale: str = "en-US"
    project_active: bool = False
    exam_active: bool = False
    last_outcome: str | None = None  # "ok" | "error" | None (unknown)
    last_score: float | None = None
    mastery_gaps: tuple[str, ...] = ()
    pending_confirmation: bool = False


def assemble_context(
    *,
    student_id: str | None,
    stage_id: str | None,
    stage_number: int | None,
    stage_name: str | None,
    stage_objective: str | None,
    action_id: str | None,
    locale: str | None,
    project_active: bool = False,
    exam_active: bool = False,
    last_outcome: str | None = None,
    last_score: float | None = None,
    mastery_gaps: tuple[str, ...] | list[str] = (),
    pending_confirmation: bool = False,
) -> TutorContext:
    """Build a context snapshot without inventing facts.

    Callers pass through whatever the authoritative sources returned; missing
    values remain ``None``/``False``/empty. Unknown locales fall back to
    ``en-US`` for rendering only — identifiers are untouched.
    """
    loc = locale if locale in ("es-CO", "en-US") else "en-US"
    outcome = last_outcome if last_outcome in ("ok", "error") else None
    return TutorContext(
        student_id=student_id,
        stage_id=stage_id,
        stage_number=stage_number,
        stage_name=stage_name,
        stage_objective=stage_objective,
        action_id=action_id,
        locale=loc,
        project_active=bool(project_active),
        exam_active=bool(exam_active),
        last_outcome=outcome,
        last_score=last_score,
        mastery_gaps=tuple(mastery_gaps),
        pending_confirmation=bool(pending_confirmation),
    )


__all__ = ["TutorContext", "assemble_context"]
