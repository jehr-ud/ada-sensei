"""Learning path, mastery assessment, and progression policy (spec 008-learning-path)."""
from __future__ import annotations

from .catalog import LearningCatalogLoader
from .models import (
    CriterionResult,
    DimensionResult,
    GateResult,
    LearningEvent,
    LearningProfile,
    MasteryAssessment,
    ProgressionDecision,
    ProgressionPolicy,
    RubricCatalog,
    StageCatalog,
    StageRubric,
)
from .onboarding import (
    OnboardingContent,
    OnboardingError,
    OnboardingStage,
    choose_starting_stage,
    get_onboarding_content,
    interpret_choice,
    render_onboarding,
    start_with_default,
    start_with_diagnostic,
)
from .progression import ProgressionPolicyEngine
from .stores import (
    LearningEventStore,
    LearningProfileStore,
    MasteryAssessmentStore,
    ProgressionDecisionStore,
)

__all__ = [
    "CriterionResult",
    "DimensionResult",
    "GateResult",
    "LearningCatalogLoader",
    "LearningEvent",
    "LearningEventStore",
    "LearningProfile",
    "LearningProfileStore",
    "MasteryAssessment",
    "MasteryAssessmentStore",
    "OnboardingContent",
    "OnboardingError",
    "OnboardingStage",
    "ProgressionDecision",
    "ProgressionDecisionStore",
    "ProgressionPolicy",
    "ProgressionPolicyEngine",
    "RubricCatalog",
    "StageCatalog",
    "StageRubric",
    "choose_starting_stage",
    "get_onboarding_content",
    "interpret_choice",
    "render_onboarding",
    "start_with_default",
    "start_with_diagnostic",
]
