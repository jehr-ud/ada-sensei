from __future__ import annotations

import json
from pathlib import Path

from ada_sensei.actions.base import ActionServices
from ada_sensei.config import Config
from ada_sensei.context import SessionContext
from ada_sensei.llm.base import LLMClient

INTERPRETATION = {
    "strengths": ["clear separation of concerns"],
    "weaknesses": ["no error handling on IO"],
    "feedback": "Good structure with room to improve error handling.",
    "recommendations": ["Add a repository boundary."],
    "next_learning_activity": "Practice error handling with sealed classes.",
}


class FakeClient(LLMClient):
    def __init__(self, payload=None):
        self.payload = payload if payload is not None else json.dumps(INTERPRETATION)

    def chat(self, messages, *, model=None, temperature=None):
        return ""

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return self.payload


class Fixture:
    @staticmethod
    def build_fixture_project(root: Path, *, wrapper: bool = True) -> Path:
        """Create a minimal Android fixture project with build artifacts."""
        proj = root / "fixture-app"
        (proj / "app" / "src" / "main").mkdir(parents=True, exist_ok=True)
        (proj / "app" / "src" / "main" / "AndroidManifest.xml").write_text(
            "<manifest />", encoding="utf-8"
        )
        (proj / "app" / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)
        (proj / "app" / "src" / "main" / "java" / "TaskRepository.kt").write_text(
            "class TaskRepository { fun add() {} }\n",
            encoding="utf-8",
        )
        (proj / "app" / "build.gradle.kts").write_text(
            "plugins { id(\"com.android.application\") }\n",
            encoding="utf-8",
        )
        if wrapper:
            (proj / "gradlew").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (proj / "gradlew").chmod(0o755)
        return proj

    @staticmethod
    def write_lint_report(proj: Path, findings: list[dict]) -> None:
        report_dir = proj / "app" / "build" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        issues = []
        for finding in findings:
            issue = (
                '<issue id="x" severity="{}" message="{}">'
                '<location file="{}" line="{}"/></issue>'
            ).format(
                finding["severity"],
                finding["message"],
                finding["file"],
                finding.get("line", "1"),
            )
            issues.append(issue)
        (report_dir / "lint-results-debug.xml").write_text(
            "<issues>" + "".join(issues) + "</issues>", encoding="utf-8"
        )

    @staticmethod
    def write_detekt_report(proj: Path, findings: list[dict]) -> None:
        report_dir = proj / "build" / "reports" / "detekt"
        report_dir.mkdir(parents=True, exist_ok=True)
        errors = []
        for finding in findings:
            errors.append(
                '<error line="{}" severity="{}" message="{}"/>'.format(
                    finding.get("line", "1"),
                    finding["severity"],
                    finding["message"],
                )
            )
        report = '<checkstyle><file name="{}">{}</file></checkstyle>'.format(
            "app/src/main/java/TaskRepository.kt", "".join(errors)
        )
        (report_dir / "detekt.xml").write_text(report, encoding="utf-8")

    @staticmethod
    def write_test_report(
        proj: Path, *, name: str = "TaskRepositoryTest", tests: int, failures: int
    ) -> None:
        report_dir = proj / "app" / "build" / "test-results" / "testDebugUnitTest"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / (name + ".xml")).write_text(
            f'<testsuite name="{name}" tests="{tests}" failures="{failures}" '
            f'errors="0"/>',
            encoding="utf-8",
        )

    @staticmethod
    def make_context(
        tmp_path,
        project_path: Path,
        student: str = "student://s1",
        current_exercise: str | None = None,
        client: LLMClient | None = None,
    ):
        config = Config(project={"path": str(project_path)})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        ctx = SessionContext(config=config, data_dir=tmp_path / "sess")
        ctx.set_student(student)
        if current_exercise:
            ctx.set_exercise(current_exercise)
        services = ActionServices.build(config, ctx, client)
        return services