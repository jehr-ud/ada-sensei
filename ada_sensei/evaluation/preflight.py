"""Read-only readiness check before a Gradle-backed workflow starts.

The evaluation and exam workflows need a runnable Android project. Detecting a
missing project, Gradle wrapper, Android manifest, build file, JDK, or Android
SDK *before* an exam attempt is created gives the student actionable reasons
instead of a silently degraded evaluation later.

This module never writes to the project and never runs Gradle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..tools.discovery import ToolDiscovery

_IGNORED_PARTS = {"build", ".gradle", ".git"}
_BUILD_FILES = {"build.gradle", "build.gradle.kts"}
_MANIFEST = "AndroidManifest.xml"


@dataclass(frozen=True)
class ProjectIssue:
    """One reason the current project cannot be evaluated."""

    code: str
    detail: str = ""


@dataclass(frozen=True)
class ProjectReadiness:
    """Result of the project readiness check."""

    project_path: str | None
    issues: tuple[ProjectIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.issues


class ProjectPreflight:
    """Checks that a project can be evaluated without executing Gradle."""

    def __init__(self, env: dict[str, str] | None = None, discovery=ToolDiscovery):
        self._env = env
        self._discovery = discovery

    def check(self, project_path: str | Path | None) -> ProjectReadiness:
        if project_path in (None, "", "."):
            return ProjectReadiness(
                project_path=None,
                issues=(ProjectIssue("no_project"),),
            )

        path = Path(str(project_path)).expanduser()
        if not path.exists():
            return ProjectReadiness(
                project_path=str(path),
                issues=(ProjectIssue("missing_path", str(path)),),
            )
        if not path.is_dir():
            return ProjectReadiness(
                project_path=str(path),
                issues=(ProjectIssue("not_directory", str(path)),),
            )

        resolved = path.resolve()
        issues: list[ProjectIssue] = []

        gradle = self._discovery.find_gradle(resolved, env=self._env)
        if not gradle.available:
            issues.append(ProjectIssue("no_gradle", gradle.message))

        if not self._has_file(resolved, _MANIFEST):
            issues.append(ProjectIssue("no_android_manifest"))
        if not self._has_build_file(resolved):
            issues.append(ProjectIssue("no_build_file"))

        jdk = self._discovery.find_jdk(env=self._env)
        if not jdk.available:
            issues.append(ProjectIssue("no_jdk", jdk.message))

        sdk = self._discovery.find_sdk(env=self._env, project=resolved)
        if not sdk.available:
            issues.append(ProjectIssue("no_android_sdk"))

        return ProjectReadiness(project_path=str(resolved), issues=tuple(issues))

    @staticmethod
    def _files(root: Path):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name
                for name in dirnames
                if not name.startswith(".") and name not in _IGNORED_PARTS
            ]
            for name in filenames:
                yield Path(dirpath) / name

    @classmethod
    def _has_file(cls, root: Path, name: str) -> bool:
        return any(path.name == name for path in cls._files(root))

    @classmethod
    def _has_build_file(cls, root: Path) -> bool:
        return any(path.name in _BUILD_FILES for path in cls._files(root))


__all__ = ["ProjectIssue", "ProjectPreflight", "ProjectReadiness"]
