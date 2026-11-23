"""Serializable contracts for isolated toolchain preparation (spec 007, RQ-EXM-064)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ToolId(StrEnum):
    android_lint = "android_lint"
    detekt = "detekt"
    ktlint = "ktlint"


class ToolStatus(StrEnum):
    READY = "READY"
    INSTALLED = "INSTALLED"
    CONFIGURED = "CONFIGURED"
    ISSUES_FOUND = "ISSUES_FOUND"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    SKIPPED_NOT_APPLICABLE = "SKIPPED_NOT_APPLICABLE"


class HealthCheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


class HealthCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: HealthCheckStatus = HealthCheckStatus.NOT_RUN
    reason: str = ""


class ToolExecutionEvidence(BaseModel):
    tool_id: ToolId
    version: str | None = None
    runtime_version: str | None = None
    coordinates: str | None = None
    checksum: str | None = None
    command: list[str] = Field(default_factory=list)
    task: str | None = None
    module: str | None = None
    variant: str | None = None
    cwd: str | None = None
    workspace: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    status: ToolStatus = ToolStatus.NOT_CONFIGURED
    health_check: HealthCheck = Field(default_factory=HealthCheck)
    report_paths: list[str] = Field(default_factory=list)
    report_hashes: dict[str, str] = Field(default_factory=dict)
    stdout_summary: str = ""
    stderr_summary: str = ""
    error_cause: str | None = None
    project_snapshot_hash: str = ""


class ToolchainManifest(BaseModel):
    policy_id: str
    policy_version: str
    resolution_policy: str
    tools: dict[ToolId, str] = Field(default_factory=dict)
    created_at: datetime
    project_snapshot_hash: str = ""
    repositories: list[str] = Field(default_factory=list)
    checksums: dict[str, str] = Field(default_factory=dict)


class ToolchainPreparationResult(BaseModel):
    ready: bool
    manifest: ToolchainManifest
    executions: list[ToolExecutionEvidence] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


__all__ = [
    "HealthCheck",
    "HealthCheckStatus",
    "ToolExecutionEvidence",
    "ToolId",
    "ToolStatus",
    "ToolchainManifest",
    "ToolchainPreparationResult",
]
