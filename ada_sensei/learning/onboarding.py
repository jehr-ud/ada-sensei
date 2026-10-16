"""First-run onboarding from the validated stage catalog (spec 008, RQ-LRN-004/005).

Application logic lives here; the TUI only renders the returned text and
forwards the student's choice back. The stage list, goal, and order always
come from the selected locale's validated catalog — never from a hardcoded
list. Choosing a starting stage never marks skipped prerequisites as
mastered, and exam records are never touched by this flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .catalog import LearningCatalogLoader
from .models import LearningProfile, StageCatalog
from .stores import LearningProfileStore


class OnboardingError(ValueError):
    """Raised for unknown stage selections or invalid onboarding configuration."""


@dataclass(frozen=True)
class OnboardingStage:
    number: int
    id: str
    title: str
    objective: str


@dataclass(frozen=True)
class OnboardingContent:
    goal_title: str
    goal_description: str
    stages: list[OnboardingStage] = field(default_factory=list)
    locale: str = "en-US"
    catalog_id: str = ""
    catalog_version: str = ""
    default_stage_id: str = ""


def get_onboarding_content(
    catalog: StageCatalog,
    locale: str,
    *,
    catalog_loader: LearningCatalogLoader | None = None,
) -> OnboardingContent:
    """Build onboarding content from a validated catalog (dynamic stage list)."""
    _ = catalog_loader  # reserved: callers may pass a loader for symmetry
    loc = locale if locale in ("es-CO", "en-US") else "en-US"
    stages = [
        OnboardingStage(
            number=s.number, id=s.id, title=s.title, objective=s.objective
        )
        for s in catalog.stages
    ]
    return OnboardingContent(
        goal_title=catalog.title,
        goal_description=catalog.description,
        stages=stages,
        locale=loc,
        catalog_id=catalog.catalog_id,
        catalog_version=catalog.catalog_version,
        default_stage_id=catalog.default_stage_id,
    )


def render_onboarding(content: OnboardingContent) -> str:
    """Render localized onboarding text: goal, dynamic stage list, choices."""
    from ..locale.ui_strings import get_ui_string

    loc = content.locale
    lines = [
        get_ui_string("onboard_title", loc),
        "",
        f"{content.goal_title}: {content.goal_description}" if content.goal_title else "",
        get_ui_string("onboard_stages", loc),
    ]
    for stage in content.stages:
        lines.append(f"  {stage.number}. {stage.title} ({stage.id})")
    lines += ["", get_ui_string("onboard_choice", loc)]
    return "\n".join(lines).strip()


def interpret_choice(text: str) -> tuple[str, str]:
    """Classify a raw onboarding reply.

    Returns ``("diagnose", "")``, ``("skip", "")``, or ``("stage", selection)``.
    Pure parsing; validation happens in the ``choose_*`` functions.
    """
    cleaned = (text or "").strip().lower()
    if cleaned in ("diagnose", "diagnostic", "diagnóstico", "diagnostico", "d"):
        return ("diagnose", "")
    if cleaned in ("skip", "omitir", "s", ""):
        return ("skip", "")
    return ("stage", (text or "").strip())


def _now():
    return datetime.now(tz=UTC)


def _build_profile(
    catalog: StageCatalog,
    student_id: str,
    locale: str,
    stage_id: str,
    *,
    diagnostic_completed: bool,
) -> LearningProfile:
    now = _now()
    return LearningProfile(
        student_id=student_id,
        catalog_id=catalog.catalog_id,
        catalog_version=catalog.catalog_version,
        current_stage_id=stage_id,
        mastered_stages=[],
        diagnostic_completed=diagnostic_completed,
        selected_locale=locale if locale in ("es-CO", "en-US") else "en-US",
        created_at=now,
        updated_at=now,
    )


def choose_starting_stage(
    profile_store: LearningProfileStore,
    catalog: StageCatalog,
    *,
    student_id: str,
    locale: str,
    selection: str,
) -> tuple[LearningProfile, list[str]]:
    """Persist an explicit starting stage; return profile + unmet prerequisites.

    ``selection`` is a stage number or stable stage id (case-insensitive).
    Unknown selections raise :class:`OnboardingError`. Skipped prerequisites
    are reported, never recorded as mastered.
    """
    cleaned = (selection or "").strip().lower()
    match: str | None = None
    for stage in catalog.stages:
        if cleaned == stage.id.lower() or cleaned == str(stage.number):
            match = stage.id
            break
    if match is None:
        valid = ", ".join(
            f"{s.number} ({s.id})" for s in catalog.stages
        )
        raise OnboardingError(
            f"unknown stage selection {selection!r}; valid stages: {valid}"
        )
    stage = next(s for s in catalog.stages if s.id == match)
    profile = _build_profile(
        catalog, student_id, locale, match, diagnostic_completed=False
    )
    profile_store.save(profile)
    return profile, list(stage.prerequisites)


def start_with_diagnostic(
    profile_store: LearningProfileStore,
    catalog: StageCatalog,
    *,
    student_id: str,
    locale: str,
) -> LearningProfile:
    """Persist the default stage and flag a requested initial diagnostic."""
    if not catalog.default_stage_id:
        raise OnboardingError("catalog has no default_stage_id for diagnostic start")
    profile = _build_profile(
        catalog,
        student_id,
        locale,
        catalog.default_stage_id,
        diagnostic_completed=True,
    )
    profile_store.save(profile)
    return profile


def start_with_default(
    profile_store: LearningProfileStore,
    catalog: StageCatalog,
    *,
    student_id: str,
    locale: str,
) -> LearningProfile:
    """Persist the default stage for students who skip the choice."""
    if not catalog.default_stage_id:
        raise OnboardingError("catalog has no default_stage_id")
    profile = _build_profile(
        catalog,
        student_id,
        locale,
        catalog.default_stage_id,
        diagnostic_completed=False,
    )
    profile_store.save(profile)
    return profile


__all__ = [
    "OnboardingContent",
    "OnboardingError",
    "OnboardingStage",
    "choose_starting_stage",
    "get_onboarding_content",
    "interpret_choice",
    "render_onboarding",
    "start_with_default",
    "start_with_diagnostic",
]
