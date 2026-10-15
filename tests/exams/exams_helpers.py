from __future__ import annotations

from pathlib import Path

from ada_sensei.actions.base import ActionServices
from ada_sensei.config import Config
from ada_sensei.context import SessionContext
from ada_sensei.evaluation import EvidenceContext
from ada_sensei.events import AppEventBus
from ada_sensei.exams.docs import ExamDocsWriter
from ada_sensei.exams.lifecycle import ExamLifecycle
from ada_sensei.exams.models import (
    ExamAttempt,
    ExamDefinition,
    ExamRequirement,
    ExamStatus,
)
from ada_sensei.exams.store import ExamStore
from ada_sensei.models import Evidence
from ada_sensei.tools.subprocess import SubprocessResult

EXAM_ID = "exam://test-exam"


def make_definition(**kwargs) -> ExamDefinition:
    requirements = kwargs.pop(
        "requirements",
        [
            ExamRequirement(
                requirement_id="req://fr1",
                description="repository with CRUD operations",
                weight=1.0,
            )
        ],
    )
    return ExamDefinition(
        exam_id=kwargs.pop("exam_id", EXAM_ID),
        title=kwargs.pop("title", "Test exam"),
        requirements=requirements,
        allowed_duration_seconds=kwargs.pop("allowed_duration_seconds", 3600),
        allowed_ask_count=kwargs.pop("allowed_ask_count", 4),
        **kwargs,
    )


def make_project(root: Path, name: str = "fixture-app") -> Path:
    proj = root / name
    pkg = proj / "app" / "src" / "main" / "java" / "com" / "example" / "app"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "TaskRepository.kt").write_text(
        "class TaskRepository { fun add() {} }\n", encoding="utf-8"
    )
    (pkg / "TaskViewModel.kt").write_text(
        "class TaskViewModel {}\n", encoding="utf-8"
    )
    (proj / "app" / "build.gradle.kts").write_text(
        'plugins { id("com.android.application") }\n', encoding="utf-8"
    )
    wrapper = proj / "gradlew"
    wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    wrapper.chmod(0o755)
    return proj


def default_evidence() -> list[Evidence]:
    return [
        Evidence(
            id="ev://structure",
            source="structure",
            type="structure",
            status="pass",
            file="app/src/main/java/com/example/app/TaskRepository.kt",
            message="found component Repository",
        ),
        Evidence(
            id="ev://compile",
            source="gradle",
            type="compilation",
            status="pass",
            file="app/build.gradle.kts",
            message="assembleDebug passed",
        ),
        Evidence(
            id="ev://test",
            source="test",
            type="unit_test",
            status="pass",
            file="app/src/test/java/com/example/app/TaskRepositoryTest.kt",
            message="5 tests passed",
        ),
        Evidence(
            id="ev://detekt",
            source="detekt",
            type="static",
            status="pass",
            file="app/build/reports/detekt/detekt.xml",
            message="no findings",
        ),
        Evidence(
            id="ev://lint",
            source="lint",
            type="static",
            status="pass",
            file="app/build/reports/lint-results-debug.xml",
            message="no findings",
        ),
    ]


def make_evidence(items: list[Evidence] | None = None) -> EvidenceContext:
    return EvidenceContext(
        project_id="project://p1",
        project_path=".",
        evidence=items if items is not None else default_evidence(),
    )


def make_attempt(**kwargs) -> ExamAttempt:
    defaults = dict(
        exam_attempt_id="exam_attempt://a1",
        student_id="student://s1",
        project_id="project://p1",
        exam_id=EXAM_ID,
        status=ExamStatus.active,
        allowed_duration_seconds=3600,
        allowed_ask_count=4,
    )
    defaults.update(kwargs)
    return ExamAttempt(**defaults)


def make_store(root: Path) -> ExamStore:
    return ExamStore(root / "data")


def make_bus() -> AppEventBus:
    return AppEventBus()


def make_lifecycle(
    store: ExamStore, bus: AppEventBus, project_root: Path | None = None
) -> ExamLifecycle:
    writer = None
    if project_root is not None:
        writer = lambda: ExamDocsWriter(project_root)  # noqa: E731
    return ExamLifecycle(store, bus, writer)


def make_context(
    tmp_path,
    project_path: Path,
    student: str = "student://s1",
    client=None,
):
    config = Config(project={"path": str(project_path)})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    ctx = SessionContext(config=config, data_dir=tmp_path / "sess")
    ctx.set_student(student)
    return ActionServices.build(config, ctx, client)


class OkRunner:
    """Fake subprocess runner that always succeeds."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, cmd, *, cwd=None, timeout=None):
        self.calls.append(list(cmd))
        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_s=0.1,
        )


STATEMENT_MARKDOWN = (
    "# Midterm Android Exam\n"
    "\n"
    "Allowed duration: 60 minutes\n"
    "Allowed /ask count: 4\n"
    "\n"
    "## Requirements\n"
    "\n"
    "- Repository with CRUD operations\n"
)


def make_statement_pdf(text: str) -> bytes:
    """A minimal dependency-free PDF whose text ``pdftext`` can recover."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    content = "BT /F1 12 Tf 72 720 Td\n"
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"({safe}) Tj T*\n"
    content += "ET\n"
    stream = content.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>\n",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\n",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for index, body in enumerate(objects, start=1):
        offsets[index] = len(out)
        out += f"{index} 0 obj\n".encode() + body + b"endobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for index in range(1, 6):
        out += f"{offsets[index]:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )
    return bytes(out)