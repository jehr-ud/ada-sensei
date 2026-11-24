from __future__ import annotations

import json
from pathlib import Path

import pytest
from ada_sensei.toolchain import (
    HealthCheckStatus,
    PolicyError,
    ToolchainManager,
    ToolId,
    ToolStatus,
    detect_project_profile,
    hash_project,
    load_policy,
)
from ada_sensei.tools.subprocess import SubprocessResult


class FakeRunner:
    def __init__(
        self,
        *,
        exit_code: int = 0,
        write_reports: bool = True,
        write_reports_on_failure: bool = False,
    ) -> None:
        self.exit_code = exit_code
        self.write_reports = write_reports
        self.write_reports_on_failure = write_reports_on_failure
        self.calls: list[tuple[list[str], str, int | None]] = []

    def run(self, cmd, *, cwd=None, timeout=None):
        self.calls.append((list(cmd), str(cwd), timeout))
        root = Path(cwd)
        if self.write_reports and (
            self.exit_code == 0 or self.write_reports_on_failure
        ):
            lint_dir = root / "app" / "build" / "reports"
            detekt_dir = root / "build" / "reports" / "detekt"
            ktlint_dir = root / "build" / "reports" / "ktlint"
            for directory in (lint_dir, detekt_dir, ktlint_dir):
                directory.mkdir(parents=True, exist_ok=True)
            (lint_dir / "lint-results-debug.xml").write_text(
                "<issues/>", encoding="utf-8"
            )
            (detekt_dir / "detekt.xml").write_text("<checkstyle/>", encoding="utf-8")
            (ktlint_dir / "ktlint-check.xml").write_text(
                "<checkstyle/>", encoding="utf-8"
            )
        return SubprocessResult(
            command=list(cmd),
            cwd=str(cwd),
            exit_code=self.exit_code,
            stdout="analysis completed",
            stderr="" if self.exit_code == 0 else "infrastructure failure",
            duration_s=0.01,
        )


def make_project(tmp_path: Path) -> Path:
    project = tmp_path / "fixture-app"
    (project / "gradle" / "wrapper").mkdir(parents=True)
    (project / "app" / "src" / "main" / "java").mkdir(parents=True)
    (project / "app" / "build").mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "gradle" / "wrapper" / "gradle-wrapper.properties").write_text(
        "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.4-bin.zip\n",
        encoding="utf-8",
    )
    (project / "gradlew").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (project / "app" / "src" / "main" / "java" / "Task.kt").write_text(
        "class Task\n", encoding="utf-8"
    )
    (project / "app" / "build.gradle.kts").write_text(
        'plugins {\n  id("com.android.application") version "8.1.4"\n'
        '  id("org.jetbrains.kotlin.android") version "1.9.22"\n}\n',
        encoding="utf-8",
    )
    (project / "settings.gradle.kts").write_text('include(":app")\n', encoding="utf-8")
    (project / ".java-version").write_text("17\n", encoding="utf-8")
    (project / "local.properties").write_text("sdk.dir=/secret\n", encoding="utf-8")
    (project / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (project / "app" / "build" / "stale.txt").write_text("old\n", encoding="utf-8")
    return project


def make_modern_project(tmp_path: Path) -> Path:
    project = make_project(tmp_path)
    (project / ".java-version").unlink()
    (project / "gradle" / "wrapper" / "gradle-wrapper.properties").write_text(
        "distributionUrl=https\\://services.gradle.org/distributions/gradle-9.5.0-bin.zip\n",
        encoding="utf-8",
    )
    (project / "app" / "build.gradle.kts").write_text(
        'plugins {\n  id("com.android.application") version "9.3.3"\n'
        '  id("org.jetbrains.kotlin.android") version "2.2.10"\n}\n'
        "android { compileOptions { sourceCompatibility = JavaVersion.VERSION_11 } }\n",
        encoding="utf-8",
    )
    return project


def pinned_policy(*, gradle: str = "8.4") -> dict:
    return {
        "policy_id": "test-pinned-toolchain",
        "policy_version": "2.1.0",
        "resolution_policy": "pinned-compatible-only",
        "repositories": ["gradlePluginPortal", "google", "mavenCentral"],
        "compatibility_matrix": [
            {
                "jdk": "17",
                "gradle": gradle,
                "kotlin": "1.9.22",
                "agp": "8.1.4",
                "tools": {
                    "android_lint": "8.1.4",
                    "detekt": "1.23.6",
                    "ktlint": "1.1.1",
                },
                "checksums": {"detekt": "sha256:abc123"},
            }
        ],
        "tools": {
            "android_lint": {
                "provider": "android_gradle_plugin",
                "required": True,
                "task_resolution": ["lint<Variant>", "lint"],
            },
            "detekt": {
                "provider": "gradle_plugin",
                "required": True,
                "version_source": "compatibility_matrix",
                "task_resolution": ["detekt"],
            },
            "ktlint": {
                "provider": "gradle_plugin_or_cli",
                "required": True,
                "version_source": "compatibility_matrix",
                "task_resolution": ["ktlintCheck"],
            },
        },
        "execution": {
            "workspace": "isolated_temporary_copy",
            "allow_global_install": False,
            "allow_source_mutation": False,
            "allow_auto_correct": False,
            "require_health_check": True,
            "require_structured_report": True,
        },
        "network": {"allow_unlisted_repositories": False},
    }


def test_empty_matrix_blocks_without_execution_or_attempt(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    before = hash_project(project)
    runner = FakeRunner()
    empty_policy = pinned_policy()
    empty_policy["compatibility_matrix"] = []
    manager = ToolchainManager(
        policy=empty_policy, runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert result.ready is False
    assert runner.calls == []
    assert not result.executions or all(
        item.status in {ToolStatus.NOT_CONFIGURED, ToolStatus.INCOMPATIBLE}
        for item in result.executions
    )
    assert all(
        item.health_check.status is HealthCheckStatus.NOT_RUN
        for item in result.executions
    )
    assert all(not item.report_paths for item in result.executions)
    assert result.manifest.tools == {}
    assert any(
        "compatibility_matrix is empty" in blocker for blocker in result.blockers
    )
    assert hash_project(project) == before
    assert not hasattr(result, "exam_attempt")


def test_pinned_policy_with_fake_runner_marks_all_tools_ready(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner()
    manager = ToolchainManager(
        policy=pinned_policy(), runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert result.ready is True, result.blockers
    assert result.blockers == []
    assert {item.tool_id for item in result.executions} == set(ToolId)
    assert all(item.status is ToolStatus.READY for item in result.executions)
    assert all(
        item.health_check.status is HealthCheckStatus.PASS for item in result.executions
    )
    assert all(item.exit_code == 0 for item in result.executions)
    assert all(item.report_paths and item.report_hashes for item in result.executions)
    assert all(
        item.project_snapshot_hash == hash_project(project)
        for item in result.executions
    )
    versions = {item.tool_id: item.version for item in result.executions}
    assert versions == {
        ToolId.android_lint: "8.1.4",
        ToolId.detekt: "1.23.6",
        ToolId.ktlint: "1.1.1",
    }
    tasks = [item.task for item in result.executions]
    assert tasks == ["lintDebug", "detekt", "ktlintCheck"]
    assert [call[0][1] for call in runner.calls] == tasks
    assert all(call[1] != str(project) for call in runner.calls)
    assert result.manifest.policy_id == "test-pinned-toolchain"
    assert result.manifest.resolution_policy == "pinned-compatible-only"
    assert result.manifest.tools == versions
    assert result.manifest.checksums["detekt"] == "sha256:abc123"
    assert any(
        "app/build/reports/lint-results-debug.xml" in key
        for key in result.manifest.checksums
    )


def test_default_policy_prepares_a_supported_project(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner()
    policy = load_policy()
    manager = ToolchainManager(
        policy=policy, runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert policy.compatibility_matrix, "default policy must pin a combination"
    assert result.ready is True, result.blockers
    assert result.blockers == []
    assert {item.tool_id for item in result.executions} == set(ToolId)
    assert all(item.status is ToolStatus.READY for item in result.executions)
    assert all(
        item.health_check.status is HealthCheckStatus.PASS for item in result.executions
    )
    versions = {item.tool_id: item.version for item in result.executions}
    assert versions == {
        ToolId.android_lint: "8.1.4",
        ToolId.detekt: "1.23.6",
        ToolId.ktlint: "1.1.1",
    }
    assert [call[0][1] for call in runner.calls] == [
        "lintDebug",
        "detekt",
        "ktlintCheck",
    ]
    assert all(call[1] != str(project) for call in runner.calls)


def test_failed_health_check_produces_execution_error_and_no_ready(
    tmp_path: Path,
) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner(exit_code=1, write_reports=False)
    manager = ToolchainManager(
        policy=pinned_policy(), runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert result.ready is False
    assert len(result.blockers) == 3
    assert all(item.status is ToolStatus.EXECUTION_ERROR for item in result.executions)
    assert all(
        item.health_check.status is HealthCheckStatus.FAIL for item in result.executions
    )
    assert all(
        item.error_cause and "1" in item.error_cause for item in result.executions
    )
    assert all(not item.report_paths for item in result.executions)
    assert all(item.exit_code == 1 for item in result.executions)


def test_analysis_findings_do_not_block_exam_start(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner(exit_code=1, write_reports_on_failure=True)
    manager = ToolchainManager(
        policy=pinned_policy(), runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert result.ready is True
    assert result.blockers == []
    assert all(
        item.status is ToolStatus.ISSUES_FOUND for item in result.executions
    )
    assert all(
        item.health_check.status is HealthCheckStatus.PASS for item in result.executions
    )


def test_missing_report_with_zero_exit_is_not_ready(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner(exit_code=0, write_reports=False)
    manager = ToolchainManager(
        policy=pinned_policy(), runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert result.ready is False
    assert all(item.status is ToolStatus.EXECUTION_ERROR for item in result.executions)
    assert all(
        "structured report" in (item.error_cause or "") for item in result.executions
    )


def test_original_project_is_never_mutated(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    before = hash_project(project)
    tracked = {
        path.relative_to(project): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }
    runner = FakeRunner()
    manager = ToolchainManager(
        policy=pinned_policy(), runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    assert hash_project(project) == before
    assert {
        path.relative_to(project): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    } == tracked
    assert result.manifest.project_snapshot_hash == before
    workspace = Path(result.executions[0].workspace)
    assert workspace != project
    assert (workspace / "gradlew").is_file()
    assert not (workspace / ".git").exists()
    assert (workspace / "local.properties").read_text(encoding="utf-8") == (
        "sdk.dir=/secret\n"
    )
    assert not (workspace / "app" / "build" / "stale.txt").exists()
    assert all(call[0][1] != str(project) for call in runner.calls)


def test_incompatible_versions_block_without_execution(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner()
    manager = ToolchainManager(
        policy=pinned_policy(gradle="7.6"),
        runner=runner,
        workspace_root=tmp_path / "ws",
    )

    result = manager.prepare(project)

    assert result.ready is False
    assert runner.calls == []
    assert all(item.status is ToolStatus.INCOMPATIBLE for item in result.executions)
    assert any(
        "no pinned compatibility entry" in blocker for blocker in result.blockers
    )
    assert any("gradle=8.4" in blocker for blocker in result.blockers)


def test_latest_version_is_rejected(tmp_path: Path) -> None:
    policy = pinned_policy()
    policy["compatibility_matrix"][0]["tools"]["detekt"] = "latest"
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")

    with pytest.raises(PolicyError, match="floating version"):
        load_policy(path)
    with pytest.raises(PolicyError, match="floating version"):
        ToolchainManager(policy=policy)

    policy = pinned_policy()
    policy["resolution_policy"] = "latest-compatible"
    path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(PolicyError, match="resolution_policy"):
        load_policy(path)


def test_no_auto_correct_tasks_are_generated(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    runner = FakeRunner()
    manager = ToolchainManager(
        policy=pinned_policy(), runner=runner, workspace_root=tmp_path / "ws"
    )

    result = manager.prepare(project)

    commands = [part.lower() for call in runner.calls for part in call[0]]
    assert not any("format" in part or "autocorrect" in part for part in commands)
    assert all(item.status is ToolStatus.READY for item in result.executions)


def test_source_compatibility_is_not_runtime_jdk(tmp_path: Path) -> None:
    project = make_modern_project(tmp_path)
    profile = detect_project_profile(project)

    assert profile.jdk is None
    assert profile.gradle == "9.5.0"
    assert profile.kotlin == "2.2.10"
    assert profile.agp == "9.3.3"


def test_default_policy_auto_configures_missing_static_tools(tmp_path: Path) -> None:
    project = make_modern_project(tmp_path)
    runner = FakeRunner()
    manager = ToolchainManager(runner=runner, workspace_root=tmp_path / "ws")

    result = manager.prepare(project)

    assert result.ready is True
    assert [call[0][-1] for call in runner.calls] == [
        "lintDebug",
        "detekt",
        "ktlintCheck",
    ]
    assert "--init-script" not in runner.calls[0][0]
    assert all("--init-script" in call[0] for call in runner.calls[1:])
    assert result.manifest.tools == {
        ToolId.android_lint: "9.3.3",
        ToolId.detekt: "2.0.0-alpha.5",
        ToolId.ktlint: "1.6.0",
    }
    detekt_script = Path(runner.calls[1][0][2])
    ktlint_script = Path(runner.calls[2][0][2])
    assert "dev.detekt:dev.detekt.gradle.plugin:2.0.0-alpha.5" in (
        detekt_script.read_text(encoding="utf-8")
    )
    ktlint_marker = (
        "org.jlleitschuh.gradle.ktlint:"
        "org.jlleitschuh.gradle.ktlint.gradle.plugin:14.2.0"
    )
    assert ktlint_marker in ktlint_script.read_text(encoding="utf-8")
    assert "reporter 'checkstyle'" in ktlint_script.read_text(encoding="utf-8")
    assert all(call[1] != str(project) for call in runner.calls)
    assert all(
        item.health_check.status is HealthCheckStatus.PASS
        for item in result.executions
    )


def test_successful_preparation_is_cached_for_repeated_panel_validation(
    tmp_path: Path,
) -> None:
    project = make_modern_project(tmp_path)
    runner = FakeRunner()
    manager = ToolchainManager(runner=runner, workspace_root=tmp_path / "ws")

    first = manager.prepare(project)
    second = manager.prepare(project)

    assert len(runner.calls) == 3
    assert second.model_dump() == first.model_dump()
