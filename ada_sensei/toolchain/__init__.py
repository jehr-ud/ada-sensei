"""Isolated, reproducible static-toolchain preparation for ADA Sensei.

This package is deterministic and LLM-free. It never mutates the student's
project tree: preparation runs in a temporary workspace and reports real
execution evidence. It is not yet wired into exam preflight.
"""

from .manager import (
    ProjectProfile,
    ToolchainManager,
    detect_project_profile,
    hash_project,
)
from .models import (
    HealthCheck,
    HealthCheckStatus,
    ToolchainManifest,
    ToolchainPreparationResult,
    ToolExecutionEvidence,
    ToolId,
    ToolStatus,
)
from .policy import (
    DEFAULT_POLICY_PATH,
    PINNED_RESOLUTION_POLICY,
    CompatibilityEntry,
    PolicyError,
    ToolchainPolicy,
    ToolPolicy,
    VersionResolution,
    load_policy,
    resolve_versions,
)

__all__ = [
    "CompatibilityEntry",
    "DEFAULT_POLICY_PATH",
    "PINNED_RESOLUTION_POLICY",
    "PolicyError",
    "ProjectProfile",
    "ToolPolicy",
    "ToolchainManager",
    "ToolchainPolicy",
    "VersionResolution",
    "detect_project_profile",
    "hash_project",
    "load_policy",
    "resolve_versions",
    "HealthCheck",
    "HealthCheckStatus",
    "ToolExecutionEvidence",
    "ToolId",
    "ToolStatus",
    "ToolchainManifest",
    "ToolchainPreparationResult",
]
