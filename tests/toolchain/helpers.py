from __future__ import annotations

from datetime import UTC, datetime

from ada_sensei.toolchain.models import (
    HealthCheck,
    HealthCheckStatus,
    ToolchainManifest,
    ToolchainPreparationResult,
    ToolExecutionEvidence,
    ToolId,
    ToolStatus,
)


class ReadyToolchainManager:
    """Deterministic test double; never touches Gradle or the student project."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.manifest = ToolchainManifest(
            policy_id="test-toolchain",
            policy_version="1.0.0",
            resolution_policy="pinned-compatible-only",
            created_at=now,
        )
        self.executions = [
            ToolExecutionEvidence(
                tool_id=tool,
                version="1.0.0",
                status=ToolStatus.READY,
                health_check=HealthCheck(status=HealthCheckStatus.PASS),
                started_at=now,
                finished_at=now,
            )
            for tool in ToolId
        ]

    def prepare(self, project_path, **kwargs) -> ToolchainPreparationResult:
        return ToolchainPreparationResult(
            ready=True,
            manifest=self.manifest,
            executions=list(self.executions),
        )


class BlockedToolchainManager(ReadyToolchainManager):
    """Deterministic test double that blocks every exam start."""

    def prepare(self, project_path, **kwargs) -> ToolchainPreparationResult:
        return ToolchainPreparationResult(
            ready=False,
            manifest=self.manifest,
            executions=list(self.executions),
            blockers=["detekt: pinned version is unavailable"],
        )
