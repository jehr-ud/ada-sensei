"""Deterministic evidence collection for Android projects (RQ-EVA-002..004,
RQ-EVA-015).

These tools never interpret and never write to the student's source tree. They
are moved out of ``actions/evaluate.py`` unchanged in behaviour so a second
workflow can reuse them without duplicating Android analysis (ADR-022).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from ..models import Evidence
from ..tools.discovery import ToolDiscovery, ToolUnavailable
from ..tools.inspector import ProjectInspector
from ..tools.subprocess import SubprocessRunner
from .models import EvaluationExecutionPolicy, EvidenceContext, ProjectContext
from .rubric import SEVERITIES

#: Unit tests only. ``connectedAndroidTest`` is never collected by default
#: (RQ-EVA-021, RQ-EVA-004).
UNIT_TEST_TASK = "testDebugUnitTest"
BUILD_TASK = "assembleDebug"
LINT_TASK = "lint"
DETEKT_TASK = "detekt"

#: Evidence types that count as the default scope (RQ-EVA-020).
SCOPE_TYPES = ("structure", "compilation", "unit_test", "android_lint", "detekt")


class AndroidProjectAnalyzer:
    """Read-only inspection of project structure and Android conventions."""

    def __init__(self, project_path: str | Path) -> None:
        self.project_path = Path(project_path).resolve()
        self.inspector = ProjectInspector(self.project_path)

    def analyze(self) -> list[Evidence]:
        evidence: list[Evidence] = [
            self._check("gradle wrapper present", "gradlew", "structure"),
            self._check(
                "Android manifest present",
                "app/src/main/AndroidManifest.xml",
                "structure",
            ),
            # The debug-variant manifest is optional: not every project creates
            # one and its absence says nothing about the student's architecture
            # or code quality.  We record it as an informational note only;
            # ``status="info"`` prevents it from lowering any dimension score
            # (RQ-EXM-010, spec.md §ArchitectureAnalyzer).
            self._check_optional(
                "debug variant manifest",
                "app/src/debug/AndroidManifest.xml",
                "structure",
            ),
            self._check("Kotlin source directory", "app/src/main/java", "structure"),
        ]
        build_files = [
            p
            for p in self.inspector.structure()
            if p == "build.gradle.kts" or p.endswith("/build.gradle.kts")
        ]
        evidence.append(
            Evidence(
                source="file",
                type="structure",
                status="pass" if build_files else "missing",
                message=(
                    "build file(s): " + ", ".join(build_files) if build_files
                    else "no build file(s) found"
                ),
            )
        )
        return evidence

    def _check_optional(self, message: str, relpath: str, type: str) -> Evidence:
        """Like ``_check`` but uses ``status="info"`` when absent.

        Optional convention files (debug variant manifests, etc.) are recorded
        for transparency but their absence must not decrease any score.
        """
        present = self.inspector.exists(relpath)
        return Evidence(
            source="file",
            type=type,
            # "info" for absent optional files; "pass" when present.
            status="pass" if present else "info",
            message=message + (" present" if present else " not present (optional)"),
            file=relpath,
        )

    def _check(self, message: str, relpath: str, type: str) -> Evidence:
        return Evidence(
            source="file",
            type=type,
            status="pass" if self.inspector.exists(relpath) else "missing",
            message=message,
            file=relpath,
        )


class GradleTool:
    """Wrapper discovery, build/compile, timeouts, subprocess capture."""

    def __init__(
        self,
        project_path: str,
        runner: SubprocessRunner | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.project_path = Path(project_path).resolve()
        self.runner = runner or SubprocessRunner()
        self._env = env

    def wrapper(self) -> Path:
        gradle = ToolDiscovery.find_gradle(self.project_path, env=self._env)
        if not gradle.available:
            raise ToolUnavailable(gradle.message)
        return Path(gradle.command or "")

    def run_task(self, task: str, timeout: int | None = None) -> Evidence:
        try:
            wrapper = self.wrapper()
        except ToolUnavailable as exc:
            return Evidence(
                source="build",
                type="compilation",
                status="missing",
                message=f"limitation: {exc}",
            )
        result = self.runner.run(
            [str(wrapper), task],
            cwd=self.project_path,
            timeout=timeout,
        )
        return result.to_evidence("build", "compilation")

    def build(self, timeout: int | None = None) -> Evidence:
        return self.run_task(BUILD_TASK, timeout=timeout)


class TestTool:
    """Unit-test execution and report collection. Never instrumented tests."""

    def __init__(
        self,
        project_path: str,
        runner: SubprocessRunner | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.project_path = Path(project_path).resolve()
        self.runner = runner or SubprocessRunner()
        self._env = env

    def _gradle(self) -> GradleTool:
        return GradleTool(str(self.project_path), runner=self.runner, env=self._env)

    def run_unit_tests(self, timeout: int | None = None) -> list[Evidence]:
        gradle_tool = self._gradle()
        try:
            command = str(gradle_tool.wrapper())
        except ToolUnavailable as exc:
            return [
                Evidence(
                    source="test",
                    type="unit_test",
                    status="missing",
                    message=f"limitation: {exc}",
                )
            ]
        result = gradle_tool.runner.run(
            [command, UNIT_TEST_TASK],
            cwd=self.project_path,
            timeout=timeout,
        )
        command_evidence = result.to_evidence("test", "unit_test")
        report_evidence = self.parse_reports()
        if not report_evidence:
            return [command_evidence]
        return [command_evidence, *report_evidence]

    def parse_reports(self) -> list[Evidence]:
        reports = self._report_files()
        if not reports:
            return []
        evidence: list[Evidence] = []
        for report in reports:
            try:
                root = ET.parse(str(report)).getroot()
            except ET.ParseError:
                continue
            for suite in root.iter("testsuite"):
                name = suite.get("name", report.stem)
                failures = int(suite.get("failures", "0"))
                errors = int(suite.get("errors", "0"))
                tests = int(suite.get("tests", "0"))
                status = "pass" if failures == 0 and errors == 0 else "fail"
                evidence.append(
                    Evidence(
                        source="test",
                        type="unit_test",
                        status=status,
                        message=f"{name}: {tests} tests, {failures} failures",
                        file=str(report),
                    )
                )
        return evidence

    def _report_files(self) -> list[Path]:
        patterns = (
            "app/build/test-results/**/*.xml",
            "build/test-results/**/*.xml",
        )
        found: list[Path] = []
        for pattern in patterns:
            found.extend(sorted(self.project_path.glob(pattern)))
        return found


class StaticAnalysisTool:
    """Android Lint and Detekt through the project's Gradle wrapper.

    Findings preserve ``ERROR``/``WARNING``/``INFO`` (RQ-EVA-015) and are
    evidence, not one-to-one grade deductions.
    """

    def __init__(
        self,
        project_path: str,
        runner: SubprocessRunner | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.project_path = Path(project_path).resolve()
        self.runner = runner or SubprocessRunner()
        self._env = env

    def _gradle(self) -> GradleTool:
        return GradleTool(str(self.project_path), runner=self.runner, env=self._env)

    def run_all(self, timeout: int | None = None) -> list[Evidence]:
        return [
            *self.run_lint(timeout=timeout),
            *self.run_detekt(timeout=timeout),
        ]

    def run_lint(self, timeout: int | None = None) -> list[Evidence]:
        gradle_tool = self._gradle()
        try:
            command = str(gradle_tool.wrapper())
        except ToolUnavailable as exc:
            return [self._unavailable("lint", "android_lint", exc)]
        result = gradle_tool.runner.run(
            [command, LINT_TASK], cwd=self.project_path, timeout=timeout
        )
        command_evidence = result.to_evidence("lint", "android_lint")
        findings = self.parse_lint_reports()
        if not findings:
            return [command_evidence]
        return [command_evidence, *findings]

    def run_detekt(self, timeout: int | None = None) -> list[Evidence]:
        gradle_tool = self._gradle()
        try:
            command = str(gradle_tool.wrapper())
        except ToolUnavailable as exc:
            return [self._unavailable("detekt", "detekt", exc)]
        result = gradle_tool.runner.run(
            [command, DETEKT_TASK], cwd=self.project_path, timeout=timeout
        )
        # A non-zero exit code from the detekt Gradle task has two very
        # different meanings:
        #   1. The task ran and found code issues → evidence of findings.
        #   2. The task does not exist in this project → Detekt is not
        #      configured; treat as a limitation, not a student failure.
        # We distinguish them by checking for the task-not-found pattern in
        # the output.  ``status="missing"`` means the tool is not available
        # for this project; it must not lower the student's score
        # (RQ-EXM-010, spec.md §Detekt).
        if result.exit_code != 0 and _detekt_not_configured(result.stdout, result.stderr):
            return [
                Evidence(
                    source="detekt",
                    type="detekt",
                    status="missing",
                    message=(
                        "limitation: detekt task not found in this project "
                        "(detekt is not configured); code quality not evaluated"
                    ),
                    command=" ".join(result.command),
                )
            ]
        command_evidence = result.to_evidence("detekt", "detekt")
        findings = self.parse_detekt_reports()
        if not findings:
            return [command_evidence]
        return [command_evidence, *findings]

    @staticmethod
    def _unavailable(source: str, type_: str, exc: Exception) -> Evidence:
        return Evidence(
            source=source,
            type=type_,
            status="missing",
            severity=None,
            message=f"limitation: {exc}",
        )

    def parse_lint_reports(self) -> list[Evidence]:
        reports = list(self.project_path.glob("app/build/reports/lint-results-*.xml"))
        findings: list[Evidence] = []
        for report in reports:
            try:
                root = ET.parse(str(report)).getroot()
            except ET.ParseError:
                continue
            for issue in root.iter("issue"):
                severity = (issue.get("severity") or "info").lower()
                if severity not in SEVERITIES:
                    severity = "info"
                location = issue.find("location")
                findings.append(
                    Evidence(
                        source="lint",
                        type="android_lint",
                        severity=severity,
                        status="fail" if severity == "error" else "pass",
                        message=issue.get("message", ""),
                        file=location.get("file") if location is not None else None,
                        line=location.get("line") if location is not None else None,
                        command=f"gradle {LINT_TASK}",
                    )
                )
        return findings

    def parse_detekt_reports(self) -> list[Evidence]:
        reports = list(self.project_path.glob("build/reports/detekt/*.xml")) + list(
            self.project_path.glob("app/build/reports/detekt/*.xml")
        )
        findings: list[Evidence] = []
        for report in reports:
            try:
                root = ET.parse(str(report)).getroot()
            except ET.ParseError:
                continue
            for file_node in root.iter("file"):
                filename = file_node.get("name")
                for error in file_node.iter("error"):
                    severity = (error.get("severity") or "info").lower()
                    if severity not in SEVERITIES:
                        severity = "info"
                    findings.append(
                        Evidence(
                            source="detekt",
                            type="detekt",
                            severity=severity,
                            status="fail" if severity == "error" else "pass",
                            message=error.get("message", ""),
                            file=filename,
                            line=error.get("line"),
                            command=f"gradle {DETEKT_TASK}",
                        )
                    )
        return findings


def _detekt_not_configured(stdout: str, stderr: str) -> bool:
    """Return True when the Gradle output indicates Detekt is not configured.

    Patterns that indicate the task was not found (not a student failure):
    - ``Task 'detekt' not found``
    - ``Could not determine the dependencies of task ':detekt'``
    - ``No tasks available`` with detekt mentioned
    - Output only contains Gradle lifecycle text with no detekt task execution

    A project where detekt ran and found issues will show task execution lines
    like ``> Task :app:detekt`` or ``> Task :detekt`` before any failure.
    """
    combined = (stdout + stderr).lower()
    # Explicit task-not-found messages
    if "task 'detekt' not found" in combined:
        return True
    if "could not determine the dependencies of task ':detekt'" in combined:
        return True
    # Gradle finished without ever executing a detekt task
    task_executed = bool(
        re.search(r">\s+task\s+:[^\s]*detekt", combined, re.I)
    )
    if not task_executed and "detekt" not in combined.split("configuration cache")[0]:
        return True
    # Only the configuration cache line mentions detekt — task never ran
    lines_mentioning_detekt = [
        line for line in combined.splitlines()
        if "detekt" in line and not line.strip().startswith("[incubating]")
        and "configuration cache" not in line
        and "task graph" not in line
    ]
    if not lines_mentioning_detekt:
        return True
    return False


def assign_evidence_ids(evidence: list[Evidence]) -> list[Evidence]:
    """Stamp stable ``ev://<n>`` provenance ids, preserving order."""
    stamped: list[Evidence] = []
    for index, item in enumerate(evidence, start=1):
        stamped.append(item.model_copy(update={"id": f"ev://{index}"}))
    return stamped


class EvidenceCollector:
    """Runs the default evaluation scope into a workflow-neutral context.

    RQ-EVA-020: project inspection, build, unit tests, Android Lint, Detekt.
    RQ-EVA-012/019: a tool that cannot run yields a ``missing`` evidence record
    and an explicit limitation, never a silent pass.
    """

    def __init__(
        self,
        project: ProjectContext,
        policy: EvaluationExecutionPolicy | None = None,
        runner: SubprocessRunner | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.project = project
        self.policy = policy or EvaluationExecutionPolicy()
        self.runner = runner
        #: Optional per-stage progress sink (RQ-EXM-048). Receives a stable
        #: stage id, never a localized string, so the engine stays free of
        #: presentation concerns.
        self._progress = progress or (lambda _stage: None)
        self.analyzer = AndroidProjectAnalyzer(project.path)
        self.gradle = GradleTool(project.path, runner=runner)
        self.tests = TestTool(project.path, runner=runner)
        self.static = StaticAnalysisTool(project.path, runner=runner)

    def collect(self) -> EvidenceContext:
        evidence: list[Evidence] = []
        limitations: list[str] = []
        commands: list[str] = []
        timeout = self.policy.timeout_seconds

        self._progress("inspection")
        evidence.extend(self.analyzer.analyze())

        if self.policy.gradle_confirmed and self.policy.run_build:
            self._progress("build")
            build = self.gradle.build(timeout=timeout)
            evidence.append(build)
            commands.append(f"gradle {BUILD_TASK}")
            if build.status == "missing":
                limitations.append(
                    "build could not execute (missing tooling/timeout): "
                    f"{build.message}"
                )
        if self.policy.gradle_confirmed and self.policy.run_unit_tests:
            self._progress("unit_tests")
            unit_evidence = self.tests.run_unit_tests(timeout=timeout)
            evidence.extend(unit_evidence)
            commands.append(f"gradle {UNIT_TEST_TASK}")
            if all(e.status == "missing" for e in unit_evidence):
                limitations.append(
                    "unit tests could not execute: "
                    f"{unit_evidence[0].message if unit_evidence else 'no evidence'}"
                )
        if self.policy.gradle_confirmed and self.policy.run_lint:
            self._progress("lint")
            evidence.extend(self.static.run_lint(timeout=timeout))
            commands.append(f"gradle {LINT_TASK}")
        if self.policy.gradle_confirmed and self.policy.run_detekt:
            self._progress("detekt")
            evidence.extend(self.static.run_detekt(timeout=timeout))
            commands.append(f"gradle {DETEKT_TASK}")

        return EvidenceContext(
            project_id=self.project.project_id,
            project_path=self.project.path,
            evidence=assign_evidence_ids(evidence),
            limitations=limitations,
            collected_at_commands=commands,
        )


__all__ = [
    "AndroidProjectAnalyzer",
    "BUILD_TASK",
    "DETEKT_TASK",
    "EvidenceCollector",
    "GradleTool",
    "LINT_TASK",
    "SCOPE_TYPES",
    "StaticAnalysisTool",
    "TestTool",
    "UNIT_TEST_TASK",
    "assign_evidence_ids",
]
