from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from ada_sensei.toolchain.models import (
    HealthCheck,
    HealthCheckStatus,
    ToolchainManifest,
    ToolchainPreparationResult,
    ToolExecutionEvidence,
    ToolId,
    ToolStatus,
)
from pydantic import ValidationError


def test_tool_status_set_is_exact() -> None:
    assert {status.value for status in ToolStatus} == {
        "READY",
        "INSTALLED",
        "CONFIGURED",
        "ISSUES_FOUND",
        "NOT_CONFIGURED",
        "NOT_AVAILABLE",
        "INCOMPATIBLE",
        "EXECUTION_ERROR",
        "SKIPPED_NOT_APPLICABLE",
    }
    assert {tool.value for tool in ToolId} == {"android_lint", "detekt", "ktlint"}
    assert {status.value for status in HealthCheckStatus} == {"PASS", "FAIL", "NOT_RUN"}


def test_all_models_round_trip_through_json() -> None:
    health = HealthCheck(status=HealthCheckStatus.PASS, reason="exit_code=0")
    evidence = ToolExecutionEvidence(
        tool_id=ToolId.detekt,
        version="1.23.6",
        runtime_version="gradle=8.4",
        coordinates="io.gitlab.arturbosch.detekt:detekt-gradle-plugin:1.23.6",
        checksum="sha256:abc",
        command=["./gradlew", "detekt"],
        task="detekt",
        module=":app",
        variant="debug",
        cwd="/tmp/workspace/project",
        workspace="/tmp/workspace",
        exit_code=0,
        status=ToolStatus.READY,
        health_check=health,
        report_paths=["build/reports/detekt/detekt.xml"],
        report_hashes={"build/reports/detekt/detekt.xml": "def"},
        project_snapshot_hash="cafe",
    )
    manifest = ToolchainManifest(
        policy_id="policy",
        policy_version="1.0.0",
        resolution_policy="pinned-compatible-only",
        tools={ToolId.detekt: "1.23.6"},
        created_at=datetime.now(UTC),
        project_snapshot_hash="cafe",
        repositories=["mavenCentral"],
        checksums={"detekt": "sha256:abc"},
    )
    result = ToolchainPreparationResult(
        ready=True,
        manifest=manifest,
        executions=[evidence],
        blockers=[],
        limitations=[],
    )

    restored = ToolchainPreparationResult.model_validate_json(result.model_dump_json())
    assert restored.ready is True
    assert restored.executions[0].tool_id is ToolId.detekt
    assert restored.executions[0].health_check.status is HealthCheckStatus.PASS
    assert restored.manifest.tools[ToolId.detekt] == "1.23.6"
    assert json.loads(result.model_dump_json())["manifest"]["policy_id"] == "policy"


def test_health_check_requires_status_and_reason() -> None:
    check = HealthCheck(status=HealthCheckStatus.FAIL, reason="no report")
    assert check.model_dump() == {"status": "FAIL", "reason": "no report"}
    with pytest.raises(ValidationError):
        HealthCheck(status="UNKNOWN")
