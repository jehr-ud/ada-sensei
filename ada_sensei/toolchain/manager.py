"""Deterministic, LLM-free static toolchain preparation (spec 007 addendum)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..tools.subprocess import SubprocessRunner
from .models import (
    HealthCheck,
    HealthCheckStatus,
    ToolchainManifest,
    ToolchainPreparationResult,
    ToolExecutionEvidence,
    ToolId,
    ToolStatus,
)
from .policy import PolicyError, ToolchainPolicy, VersionResolution, load_policy

_DEFAULT_TIMEOUT_SECONDS = 600
_EXCLUDED_NAMES = (
    ".git",
    ".gradle",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "build",
    "node_modules",
    ".DS_Store",
    "local.properties",
    ".env",
    "secrets",
    "secrets.yml",
    "secrets.yaml",
    "credentials.json",
    "*.jks",
    "*.keystore",
    "*.pem",
)
_SECRET_SUFFIXES = (".jks", ".keystore", ".pem")
_TOOL_ORDER = (ToolId.android_lint, ToolId.detekt, ToolId.ktlint)
_DEFAULT_TASKS = {
    ToolId.android_lint: ["lint<Variant>", "lint"],
    ToolId.detekt: ["detekt", "detekt<Variant>"],
    ToolId.ktlint: ["ktlintCheck", "check"],
}
_COORDINATES = {
    ToolId.android_lint: "com.android.tools.build:gradle",
    ToolId.detekt: "io.gitlab.arturbosch.detekt:detekt-gradle-plugin",
    ToolId.ktlint: "com.pinterest:ktlint",
}
_REPORT_GLOBS = {
    ToolId.android_lint: ("**/lint-results*.xml", "**/lint-results*.html"),
    ToolId.detekt: (
        "**/detekt*.xml",
        "**/*detekt*.sarif",
        "**/detekt*.html",
        "**/detekt*.json",
    ),
    ToolId.ktlint: (
        "**/*ktlint*.xml",
        "**/ktlint*.sarif",
        "**/ktlint*.json",
        "**/ktlint*.html",
    ),
}
_FORBIDDEN_TASK_TOKENS = (
    "format",
    "autocorrect",
    "auto-correct",
    "--fix",
    "ktlintformat",
)
_KOTLIN_PATTERNS = (
    re.compile(r"kotlin\([\"']android[\"']\)\s+version\s+[\"']([^\"']+)[\"']"),
    re.compile(
        r"id\(?[\"']org\.jetbrains\.kotlin\.[a-z]+[\"']\)?\s+version\s+[\"']([^\"']+)[\"']"
    ),
    re.compile(r"kotlin_version\s*[=:]\s*[\"']?([0-9][^\s\"']*)"),
)
_AGP_PATTERNS = (
    re.compile(
        r"id\(?[\"']com\.android\.(?:application|library)[\"']\)?\s+version\s+[\"']([^\"']+)[\"']"
    ),
    re.compile(r"classpath\(?[\"']com\.android\.tools\.build:gradle:([^\"']+)[\"']"),
)
_TOML_KOTLIN = re.compile(r"^\s*kotlin(?:-version)?\s*=\s*[\"']([^\"']+)[\"']", re.M)
_TOML_AGP = re.compile(
    r"^\s*(?:agp|android-gradle-plugin|android_gradle_plugin)\s*=\s*[\"']([^\"']+)[\"']",
    re.M,
)
_TASK_PATTERN = re.compile(
    r"\b(lint[A-Za-z0-9]*|detekt[A-Za-z0-9]*|ktlint[A-Za-z0-9]*)\b"
)
_REPOSITORY_GROOVY = {
    "gradlePluginPortal": "gradlePluginPortal()",
    "mavenCentral": "mavenCentral()",
    "google": "google()",
}


class ProjectProfile(BaseModel):
    jdk: str | None = None
    gradle: str | None = None
    kotlin: str | None = None
    agp: str | None = None
    wrapper: bool = False
    modules: list[str] = Field(default_factory=list)
    variant: str = "debug"
    tasks: list[str] = Field(default_factory=list)

    def detected_versions(self) -> dict[str, str | None]:
        return {
            "jdk": self.jdk,
            "gradle": self.gradle,
            "kotlin": self.kotlin,
            "agp": self.agp,
        }


class ToolchainManager:
    def __init__(
        self,
        policy: ToolchainPolicy | Mapping[str, Any] | str | Path | None = None,
        runner: Any | None = None,
        cache_dir: str | Path | None = None,
        workspace_root: str | Path | None = None,
    ) -> None:
        self.policy = self._coerce_policy(policy)
        self.runner = runner if runner is not None else SubprocessRunner()
        self.workspace_root = Path(workspace_root) if workspace_root else None
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir)
        elif self.workspace_root is not None:
            self.cache_dir = self.workspace_root / "cache"
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "ada-sensei-toolchain-cache"
        self._result_cache: dict[tuple[str, ...], ToolchainPreparationResult] = {}

    @staticmethod
    def _coerce_policy(
        policy: ToolchainPolicy | Mapping[str, Any] | str | Path | None,
    ) -> ToolchainPolicy:
        if policy is None:
            return load_policy()
        if isinstance(policy, ToolchainPolicy):
            return policy
        if isinstance(policy, (str, Path)):
            return load_policy(policy)
        try:
            return ToolchainPolicy.model_validate(dict(policy))
        except (PolicyError, ValueError) as exc:
            raise PolicyError(f"invalid injected toolchain policy: {exc}") from exc

    def prepare(
        self,
        project_path: str | Path,
        *,
        variant: str | None = None,
        modules: list[str] | str | None = None,
    ) -> ToolchainPreparationResult:
        project = Path(project_path).resolve()
        limitations: list[str] = []
        if not project.is_dir():
            return self._blocked_result(
                None,
                ToolchainPolicy(),
                VersionResolution(),
                [f"project path does not exist or is not a directory: {project}"],
                limitations,
            )

        snapshot_hash = _hash_project(project)
        profile = detect_project_profile(project, variant=variant, modules=modules)
        limitations.extend(_detection_limitations(profile))
        resolution = self.policy.resolve_versions(profile.detected_versions())
        cache_key = self._cache_key(
            project, snapshot_hash, variant, modules, resolution
        )
        cached = self._result_cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(deep=True)

        if resolution.blockers or any(
            status not in {ToolStatus.INSTALLED, ToolStatus.READY}
            for status in resolution.statuses.values()
        ):
            return self._blocked_result(
                project,
                self.policy,
                resolution,
                resolution.blockers
                or ["toolchain resolution did not yield pinned versions"],
                limitations,
            )

        workspace = self._isolated_workspace(project)
        sdk_property = _isolated_sdk_property(project, workspace)
        if sdk_property is not None:
            limitations.append(
                "Android SDK path was forwarded to the isolated workspace "
                "without copying other local.properties values"
            )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        limitations.append(
            "analysis ran in an isolated temporary copy; "
            "no task could rewrite the original tree"
        )

        executions = []
        for tool in self.policy.required_tools():
            init_script = self._write_init_script(workspace.parent, tool, resolution)
            executions.append(
                self._execute_tool(
                    tool, profile, resolution, workspace, snapshot_hash, init_script
                )
            )
        if _hash_project(project) != snapshot_hash:
            executions[-1:] = []
            return self._blocked_result(
                project,
                self.policy,
                resolution,
                [
                    "the original project changed during toolchain preparation; "
                    "no toolchain is declared READY"
                ],
                limitations,
                executions=[],
                snapshot_hash=snapshot_hash,
            )

        blockers = [
            f"{item.tool_id.value}: {item.error_cause or item.health_check.reason}"
            for item in executions
            if item.status not in {ToolStatus.READY, ToolStatus.ISSUES_FOUND}
            or item.health_check.status != HealthCheckStatus.PASS
        ]
        manifest = self._manifest(self.policy, resolution, snapshot_hash, executions)
        result = ToolchainPreparationResult(
            ready=not blockers,
            manifest=manifest,
            executions=executions,
            blockers=blockers,
            limitations=limitations,
        )
        if result.ready:
            self._result_cache[cache_key] = result.model_copy(deep=True)
        return result

    def _cache_key(
        self,
        project: Path,
        snapshot_hash: str,
        variant: str | None,
        modules: list[str] | str | None,
        resolution: VersionResolution,
    ) -> tuple[str, ...]:
        if isinstance(modules, str):
            normalized_modules = (modules,)
        elif modules is None:
            normalized_modules = ()
        else:
            normalized_modules = tuple(sorted(modules))
        return (
            str(project),
            snapshot_hash,
            variant or "",
            *normalized_modules,
            self.policy.model_dump_json(),
            resolution.model_dump_json(),
        )

    def _write_init_script(
        self, base: Path, tool: ToolId, resolution: VersionResolution
    ) -> Path | None:
        entry = resolution.entry
        if entry is None:
            return None
        plugin = entry.plugins.get(tool.value)
        if plugin is None:
            return None
        declarations = [
            declaration
            for declaration in (
                _REPOSITORY_GROOVY.get(name) for name in self.policy.repositories
            )
            if declaration
        ]

        def repositories(indent: int) -> str:
            return "\n".join(f"{' ' * indent}{item}" for item in declarations)

        classpath = f"{plugin.marker}:{plugin.version}"
        if tool is ToolId.ktlint:
            ktlint_version = plugin.core_version or entry.version_for(tool)
            extension = f"""
            def ktlintExtension = project.extensions.findByName('ktlint')
            if (ktlintExtension != null) {{
                ktlintExtension.version.set('{ktlint_version}')
                ktlintExtension.reporters {{
                    reporter 'checkstyle'
                }}
            }}"""
        else:
            extension = ""
        script = f"""initscript {{
    repositories {{
{repositories(8)}
    }}
    dependencies {{
        classpath '{classpath}'
    }}
}}
allprojects {{
    buildscript {{
        repositories {{
{repositories(12)}
        }}
        dependencies {{
            classpath '{classpath}'
        }}
    }}
    afterEvaluate {{ project ->
        def hasKotlinSources = project.file('src/main/kotlin').exists() ||
            project.file('src/test/kotlin').exists() ||
            project.file('src/main/java').exists() ||
            project.file('src/test/java').exists()
        if (!hasKotlinSources) {{
            return
        }}
        project.pluginManager.apply('{plugin.id}'){extension}
    }}
}}
"""
        path = base / f"ada-sensei-{tool.value}-init.gradle"
        path.write_text(script, encoding="utf-8")
        return path

    def _isolated_workspace(self, project: Path) -> Path:
        if self.workspace_root is not None:
            self.workspace_root.mkdir(parents=True, exist_ok=True)
        base = Path(
            tempfile.mkdtemp(prefix="ada-sensei-toolchain-", dir=self.workspace_root)
        )
        workspace = base / "project"
        shutil.copytree(
            project,
            workspace,
            ignore=shutil.ignore_patterns(*_EXCLUDED_NAMES),
            symlinks=False,
        )
        return workspace

    def _execute_tool(
        self,
        tool: ToolId,
        profile: ProjectProfile,
        resolution: VersionResolution,
        workspace: Path,
        snapshot_hash: str,
        init_script: Path | None,
    ) -> ToolExecutionEvidence:
        cfg = self.policy.tools.get(tool)
        task = _select_task(
            tool, profile, cfg.task_resolution if cfg else [], profile.variant
        )
        command = ["./gradlew" if profile.wrapper else "gradle"]
        if init_script is not None:
            command.extend(["--init-script", str(init_script)])
        command.append(task)
        version = resolution.versions.get(tool)
        coordinate = _COORDINATES[tool]
        if version:
            coordinate = f"{coordinate}:{version}"
        entry = resolution.entry
        checksum = entry.checksums.get(tool.value) if entry else None
        if checksum is None and entry:
            checksum = entry.checksums.get(coordinate)
        common = {
            "tool_id": tool,
            "version": version,
            "runtime_version": _runtime_version(profile),
            "coordinates": coordinate,
            "checksum": checksum,
            "command": command,
            "task": task,
            "module": profile.modules[0] if profile.modules else None,
            "variant": profile.variant,
            "cwd": str(workspace),
            "workspace": str(workspace),
            "project_snapshot_hash": snapshot_hash,
        }
        started = datetime.now(UTC)
        try:
            result = self.runner.run(
                command, cwd=str(workspace), timeout=_DEFAULT_TIMEOUT_SECONDS
            )
        except Exception as exc:
            return ToolExecutionEvidence(
                **common,
                started_at=started,
                finished_at=datetime.now(UTC),
                exit_code=None,
                status=ToolStatus.EXECUTION_ERROR,
                health_check=HealthCheck(
                    status=HealthCheckStatus.FAIL,
                    reason=f"runner raised {type(exc).__name__}: {exc}",
                ),
                error_cause=f"{type(exc).__name__}: {exc}",
            )
        finished = datetime.now(UTC)
        exit_code = getattr(result, "exit_code", None)
        stdout = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""
        reports = _valid_reports(
            workspace, tool, cfg.report_paths if cfg else [], result, profile
        )
        report_hashes = {path: _file_hash(workspace / path) for path in reports}
        analyzed = bool(reports) and exit_code in {0, 1} and not getattr(
            result, "timed_out", False
        )
        if analyzed:
            findings = _count_findings(workspace, reports)
            status = ToolStatus.READY if exit_code == 0 else ToolStatus.ISSUES_FOUND
            health = HealthCheck(
                status=HealthCheckStatus.PASS,
                reason=(
                    f"exit_code={exit_code}; {len(reports)} structured report(s) "
                    f"validated; {findings} finding(s)"
                ),
            )
            error_cause = None
        else:
            reason = _failure_reason(
                exit_code, reports, getattr(result, "timed_out", False)
            )
            health = HealthCheck(status=HealthCheckStatus.FAIL, reason=reason)
            status = ToolStatus.EXECUTION_ERROR
            error_cause = reason
        return ToolExecutionEvidence(
            **common,
            started_at=started,
            finished_at=finished,
            exit_code=exit_code,
            status=status,
            health_check=health,
            report_paths=reports,
            report_hashes=report_hashes,
            stdout_summary=_summarize(stdout),
            stderr_summary=_summarize(stderr),
            error_cause=error_cause,
        )

    def _manifest(
        self,
        policy: ToolchainPolicy,
        resolution: VersionResolution,
        snapshot_hash: str,
        executions: list[ToolExecutionEvidence] | None = None,
    ) -> ToolchainManifest:
        checksums = dict(resolution.entry.checksums) if resolution.entry else {}
        checksums.pop("project_snapshot", None)
        for item in executions or []:
            checksums.update(item.report_hashes)
        return ToolchainManifest(
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            resolution_policy=policy.resolution_policy,
            tools={
                tool: version
                for tool, version in resolution.versions.items()
                if version
            },
            created_at=datetime.now(UTC),
            project_snapshot_hash=snapshot_hash,
            repositories=list(policy.repositories),
            checksums=checksums,
        )

    def _blocked_result(
        self,
        project: Path | None,
        policy: ToolchainPolicy,
        resolution: VersionResolution,
        blockers: list[str],
        limitations: list[str],
        *,
        executions: list[ToolExecutionEvidence] | None = None,
        snapshot_hash: str | None = None,
    ) -> ToolchainPreparationResult:
        if snapshot_hash is None:
            snapshot_hash = _hash_project(project) if project is not None else ""
        profile = (
            detect_project_profile(project) if project is not None else ProjectProfile()
        )
        if executions is None:
            executions = [
                ToolExecutionEvidence(
                    tool_id=tool,
                    version=resolution.versions.get(tool),
                    runtime_version=_runtime_version(profile),
                    status=resolution.statuses.get(tool, ToolStatus.NOT_CONFIGURED),
                    project_snapshot_hash=snapshot_hash,
                    error_cause=blockers[0] if blockers else None,
                    health_check=HealthCheck(status=HealthCheckStatus.NOT_RUN),
                )
                for tool in policy.required_tools()
            ]
        return ToolchainPreparationResult(
            ready=False,
            manifest=self._manifest(policy, resolution, snapshot_hash, executions),
            executions=executions,
            blockers=list(blockers),
            limitations=list(limitations),
        )


def detect_project_profile(
    project_path: str | Path,
    *,
    variant: str | None = None,
    modules: list[str] | str | None = None,
) -> ProjectProfile:
    project = Path(project_path)
    if not project.is_dir():
        return ProjectProfile()
    build_files = [
        path
        for path in sorted(project.rglob("*"))
        if path.is_file() and not _is_excluded(path, project) and _is_build_file(path)
    ]
    texts = [(path, _read_text(path)) for path in build_files]
    all_text = "\n".join(text for _, text in texts)
    toml_text = "\n".join(
        text for path, text in texts if path.name == "libs.versions.toml"
    )

    gradle = None
    wrapper_properties = project / "gradle" / "wrapper" / "gradle-wrapper.properties"
    if wrapper_properties.is_file():
        match = re.search(
            r"gradle-([0-9][0-9A-Za-z.]*)-", _read_text(wrapper_properties)
        )
        gradle = match.group(1) if match else None

    jdk = None
    java_version = project / ".java-version"
    if java_version.is_file():
        lines = _read_text(java_version).strip().splitlines()
        jdk = lines[0].strip() if lines else None
    if jdk is None:
        match = re.search(
            r"org\.gradle\.java\.home=[^\n]*?(?:jdk|java)-?(\d+)", all_text, re.I
        )
        jdk = match.group(1) if match else None
    if jdk is None:
        match = re.search(r"jvmToolchain\((\d+)\)", all_text)
        if match:
            jdk = match.group(1)

    kotlin = _first_match(_KOTLIN_PATTERNS, all_text) or _first_match(
        [_TOML_KOTLIN], toml_text
    )
    agp = _first_match(_AGP_PATTERNS, all_text) or _first_match([_TOML_AGP], toml_text)

    if isinstance(modules, str):
        detected_modules = [modules]
    elif modules is not None:
        detected_modules = list(modules)
    else:
        detected_modules = []
        for path, text in texts:
            if path.name.startswith("settings.gradle"):
                detected_modules.extend(
                    match.strip().strip("\"'")
                    for match in re.findall(
                        r"include\s*\(?\s*[\"']([^\"']+)[\"']", text
                    )
                )
        if not detected_modules:
            detected_modules = [
                f":{path.parent.name}"
                for path in build_files
                if path.name.startswith("build.gradle") and path.parent != project
            ]
        detected_modules = sorted(set(detected_modules))

    tasks = sorted(set(_TASK_PATTERN.findall(all_text)))
    return ProjectProfile(
        jdk=jdk,
        gradle=gradle,
        kotlin=kotlin,
        agp=agp,
        wrapper=(project / "gradlew").is_file(),
        modules=detected_modules,
        variant=variant or "debug",
        tasks=tasks,
    )


def _isolated_sdk_property(project: Path, workspace: Path) -> str | None:
    source = project / "local.properties"
    if not source.is_file():
        return None
    for raw in _read_text(source).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "sdk.dir" and value.strip():
            sdk_dir = value.strip()
            (workspace / "local.properties").write_text(
                f"sdk.dir={sdk_dir}\n", encoding="utf-8"
            )
            return sdk_dir
    return None


def hash_project(project_path: str | Path) -> str:
    return _hash_project(Path(project_path))


def _hash_project(project: Path | None) -> str:
    if project is None or not project.is_dir():
        return ""
    digest = hashlib.sha256()
    for path in sorted(project.rglob("*")):
        if not path.is_file() or path.is_symlink() or _is_excluded(path, project):
            continue
        relative = path.relative_to(project).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _is_excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return any(
        part in _EXCLUDED_NAMES or part.endswith(_SECRET_SUFFIXES)
        for part in relative.parts
    )


def _is_build_file(path: Path) -> bool:
    return (
        path.name.startswith("build.gradle")
        or path.name.startswith("settings.gradle")
        or path.name in {"gradle.properties", "libs.versions.toml", ".java-version"}
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _first_match(patterns: list[re.Pattern[str]], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _detection_limitations(profile: ProjectProfile) -> list[str]:
    limitations: list[str] = []
    for key, value in profile.detected_versions().items():
        if value is None:
            limitations.append(
                f"{key} version could not be detected from read-only project files; "
                "compatibility was resolved with the remaining pinned constraints"
            )
    limitations.append(
        "Gradle task availability was inferred from policy and build files; "
        "READY requires a real execution and a validated structured report"
    )
    return limitations


def _select_task(
    tool: ToolId, profile: ProjectProfile, configured: list[str], variant: str
) -> str:
    candidates = configured or _DEFAULT_TASKS[tool]
    expanded: list[str] = []
    for candidate in candidates:
        expanded.append(
            candidate.replace("<Variant>", variant.title()).replace(
                "<variant>", variant
            )
        )
    available = set(profile.tasks)
    for candidate in expanded:
        if candidate in available:
            task = candidate
            break
    else:
        task = expanded[0]
    if any(token in task.lower() for token in _FORBIDDEN_TASK_TOKENS):
        raise PolicyError(
            f"forbidden source-mutating task configured for {tool.value}: {task}"
        )
    return task


def _runtime_version(profile: ProjectProfile) -> str:
    return ", ".join(
        f"{key}={value or 'undetected'}"
        for key, value in profile.detected_versions().items()
    )


def _valid_reports(
    workspace: Path,
    tool: ToolId,
    configured: list[str],
    result: Any,
    profile: ProjectProfile,
) -> list[str]:
    candidates: list[Path] = []
    for raw in list(getattr(result, "report_paths", None) or []):
        candidates.append(_resolve_report(workspace, str(raw), profile))
    for raw in configured:
        candidates.append(_resolve_report(workspace, raw, profile))
    for pattern in _REPORT_GLOBS[tool]:
        candidates.extend(sorted(workspace.rglob(pattern)))

    valid: set[str] = set()
    for candidate in candidates:
        if not candidate.is_file() or not _is_report_valid(candidate):
            continue
        try:
            valid.add(candidate.relative_to(workspace).as_posix())
        except ValueError:
            valid.add(candidate.as_posix())
    return sorted(valid)


def _resolve_report(workspace: Path, raw: str, profile: ProjectProfile) -> Path:
    module = profile.modules[0].lstrip(":") if profile.modules else ""
    expanded = (
        raw.replace("<module>", module)
        .replace("<variant>", profile.variant)
        .replace("<Variant>", profile.variant.title())
    )
    candidate = Path(expanded)
    return candidate if candidate.is_absolute() else workspace / candidate


def _is_report_valid(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not text.strip():
        return False
    suffix = path.suffix.lower()
    try:
        if suffix == ".xml":
            ET.fromstring(text)
            return True
        if suffix in {".json", ".sarif"}:
            json.loads(text)
            return True
        if suffix == ".html":
            return "<html" in text.lower() or "<body" in text.lower()
    except (ET.ParseError, json.JSONDecodeError, ValueError):
        return False
    return False


def _count_findings(workspace: Path, reports: list[str]) -> int:
    findings = 0
    for relative in reports:
        path = workspace / relative
        if path.suffix.lower() != ".xml":
            continue
        try:
            root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
        except ET.ParseError:
            continue
        findings += sum(
            1 for item in root.iter() if item.tag in {"error", "issue"}
        )
    return findings


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _summarize(text: str, limit: int = 2000) -> str:
    return text[:limit]


def _failure_reason(exit_code: int | None, reports: list[str], timed_out: bool) -> str:
    if timed_out:
        return "tool execution timed out"
    if exit_code != 0:
        return f"tool exited with code {exit_code}"
    return "tool exited successfully but no valid structured report was generated"


__all__ = [
    "ProjectProfile",
    "ToolchainManager",
    "detect_project_profile",
    "hash_project",
]
