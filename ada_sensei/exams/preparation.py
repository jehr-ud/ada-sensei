"""Read-only exam preparation validation.

This is deliberately an application service rather than a TUI helper: direct
CLI and Textual flows must enforce the same preconditions before an attempt can
be created.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..evaluation.preflight import ProjectPreflight
from .definition import ExamDefinitionLoader
from .models import ExamDefinition, ExamDefinitionError
from .store import ExamStore


@dataclass(frozen=True)
class ExamPreparationStatus:
    student_ready: bool
    project_path: str | None
    project_ready: bool
    project_blockers: tuple[str, ...]
    instructions_path: str | None
    instructions_ready: bool
    instruction_blockers: tuple[str, ...]
    active_exam: bool
    ready_to_start: bool
    definition: ExamDefinition | None = None

    @property
    def blockers(self) -> tuple[str, ...]:
        result: list[str] = []
        if not self.student_ready:
            result.append("no_student")
        result.extend(self.project_blockers)
        result.extend(self.instruction_blockers)
        if self.active_exam:
            result.append("active_exam")
        return tuple(result)


class ExamPreparationService:
    """Validates configured paths without starting an exam or writing state."""

    def __init__(self, services, *, env: dict[str, str] | None = None) -> None:
        self.services = services
        self._env = env
        self.loader = ExamDefinitionLoader()

    def validate(self) -> ExamPreparationStatus:
        context = self.services.context
        project_path = context.project_path or self._configured_project_path()
        readiness = ProjectPreflight(env=self._env).check(project_path)
        project_blockers = tuple(issue.code for issue in readiness.issues)

        instructions_path = context.instructions_path
        definition, instruction_blockers = self._instructions(instructions_path)
        store = ExamStore(self.services.data_dir)
        # Do not rely only on the in-memory session pointer: after a UI restart
        # the persisted attempt remains authoritative.
        active = store.active_for(context.exam_attempt_id)
        if active is None:
            for attempt_id in store.list_ids():
                candidate = store.get(attempt_id)
                if candidate is not None and candidate.is_active:
                    active = candidate
                    break
        student_ready = bool(context.student_id)
        project_ready = readiness.ready
        instructions_ready = definition is not None and not instruction_blockers
        return ExamPreparationStatus(
            student_ready=student_ready,
            project_path=readiness.project_path or project_path,
            project_ready=project_ready,
            project_blockers=project_blockers,
            instructions_path=instructions_path,
            instructions_ready=instructions_ready,
            instruction_blockers=instruction_blockers,
            active_exam=active is not None,
            ready_to_start=(
                student_ready
                and project_ready
                and instructions_ready
                and active is None
            ),
            definition=definition,
        )

    def _configured_project_path(self) -> str | None:
        path = getattr(self.services.config.project, "path", None)
        return None if path in (None, "", ".") else str(path)

    def _instructions(
        self, configured: str | None
    ) -> tuple[ExamDefinition | None, tuple[str, ...]]:
        if not configured:
            return None, ("no_instructions",)
        path = Path(configured)
        if path.suffix.lower() != ".md":
            return None, ("instructions_not_markdown",)
        if not path.exists() or not path.is_file():
            return None, ("instructions_missing",)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None, ("instructions_unreadable",)
        if not text.strip():
            return None, ("instructions_empty",)
        try:
            return self.loader.load(path, exam_id=None), ()
        except ExamDefinitionError:
            return None, ("instructions_invalid",)


__all__ = ["ExamPreparationService", "ExamPreparationStatus"]
