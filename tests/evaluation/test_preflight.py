"""Project readiness preflight (exam start guard).

The TUI checks this after the student confirms exam start, before an attempt is
created. Each issue must be actionable and none of the checks may run Gradle or
write to the project.
"""

from __future__ import annotations

from pathlib import Path

from ada_sensei.evaluation.preflight import ProjectPreflight
from ada_sensei.tools.discovery import Tool, ToolDiscovery


class FakeDiscovery:
    def __init__(self, *, gradle=True, jdk=True, sdk=True):
        self.gradle = gradle
        self.jdk = jdk
        self.sdk = sdk

    def find_gradle(self, project=None, env=None):
        if self.gradle:
            return Tool(
                name="gradle",
                command=str(Path(project) / "gradlew"),
                available=True,
            )
        return Tool(
            name="gradle",
            command=None,
            available=False,
            message="gradle wrapper or gradle not found",
        )

    def find_jdk(self, env=None):
        if self.jdk:
            return Tool(name="jdk", command="java", version="17", available=True)
        return Tool(
            name="jdk",
            command=None,
            available=False,
            message="no JDK 17+ found (JAVA_HOME or PATH)",
        )

    def find_sdk(self, env=None, project=None):
        if self.sdk:
            return Tool(name="android-sdk", command="/sdk", available=True)
        return Tool(
            name="android-sdk",
            command=None,
            available=False,
            message="Android SDK not found",
        )


def _project(root: Path) -> Path:
    project = root / "app-project"
    project.mkdir()
    (project / "gradlew").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (project / "build.gradle.kts").write_text("", encoding="utf-8")
    (project / "app/src/main").mkdir(parents=True)
    (project / "app/src/main/AndroidManifest.xml").write_text(
        "<manifest/>", encoding="utf-8"
    )
    return project


def test_ready_project_has_no_issues(tmp_path):
    readiness = ProjectPreflight(discovery=FakeDiscovery()).check(_project(tmp_path))

    assert readiness.ready
    assert readiness.issues == ()


def test_no_project_configured():
    readiness = ProjectPreflight(discovery=FakeDiscovery()).check(None)

    assert not readiness.ready
    assert [issue.code for issue in readiness.issues] == ["no_project"]


def test_missing_path_and_not_directory(tmp_path):
    missing = tmp_path / "missing"
    readiness = ProjectPreflight(discovery=FakeDiscovery()).check(missing)
    assert [issue.code for issue in readiness.issues] == ["missing_path"]

    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    readiness = ProjectPreflight(discovery=FakeDiscovery()).check(file_path)
    assert [issue.code for issue in readiness.issues] == ["not_directory"]


def test_non_android_project_reports_structural_reasons(tmp_path):
    project = tmp_path / "empty"
    project.mkdir()

    readiness = ProjectPreflight(discovery=FakeDiscovery()).check(project)

    codes = [issue.code for issue in readiness.issues]
    assert "no_android_manifest" in codes
    assert "no_build_file" in codes


def test_missing_toolchain_reports_reasons(tmp_path):
    discovery = FakeDiscovery(gradle=False, jdk=False, sdk=False)

    readiness = ProjectPreflight(discovery=discovery).check(_project(tmp_path))

    codes = [issue.code for issue in readiness.issues]
    assert codes == ["no_gradle", "no_jdk", "no_android_sdk"]
    assert all(
        issue.detail
        for issue in readiness.issues
        if issue.code != "no_android_sdk"
    )


def test_literal_sdk_dir_satisfies_preflight(tmp_path):
    class LiteralSdkDiscovery(FakeDiscovery):
        def find_sdk(self, env=None, project=None):
            return ToolDiscovery.find_sdk(env=env, project=project)

    project = _project(tmp_path)
    value = r"C\:\\Users\\LENOVO\\AppData\\Local\\Android\\Sdk"
    (project / "local.properties").write_text(
        f"sdk.dir={value}\n", encoding="utf-8"
    )

    readiness = ProjectPreflight(discovery=LiteralSdkDiscovery()).check(project)

    assert "no_android_sdk" not in [issue.code for issue in readiness.issues]
