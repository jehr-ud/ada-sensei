"""Read-only exam preparation validation.

This is deliberately an application service rather than a TUI helper: direct
CLI and Textual flows must enforce the same preconditions before an attempt can
be created.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..evaluation.preflight import ProjectPreflight, resolve_active_project_path
from ..locale.ui_strings import get_ui_string
from ..resources.paths import (
    ResourceKind,
    ResourcePathError,
    ResourceResolver,
)
from ..toolchain.manager import ToolchainManager
from ..toolchain.models import ToolchainPreparationResult
from .definition import ExamDefinitionLoader, ExamDefinitionValidationError
from .models import ExamDefinition
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
    exam_definition_path: str | None = None
    exam_definition_ready: bool = False
    exam_definition_blockers: tuple[str, ...] = ()
    definition: ExamDefinition | None = None
    toolchain_ready: bool = False
    toolchain_blockers: tuple[str, ...] = ()
    toolchain_preparation: ToolchainPreparationResult | None = None

    @property
    def blockers(self) -> tuple[str, ...]:
        result: list[str] = []
        if not self.student_ready:
            result.append("no_student")
        result.extend(self.project_blockers)
        result.extend(self.instruction_blockers)
        result.extend(self.exam_definition_blockers)
        if self.active_exam:
            result.append("active_exam")
        if self.project_ready and not self.toolchain_ready:
            result.append("toolchain_not_ready")
        return tuple(result)


class ExamPreparationService:
    """Validates configured paths without starting an exam or writing state."""

    def __init__(
        self,
        services,
        *,
        env: dict[str, str] | None = None,
        toolchain: ToolchainManager | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.services = services
        self._env = env
        config = getattr(services, "config", None)
        self._base_dir = getattr(config, "base_dir", None)
        self.loader = ExamDefinitionLoader()
        self.toolchain = toolchain if toolchain is not None else ToolchainManager()
        self._progress = progress

    def validate(
        self,
        *,
        require_exam_definition: bool = True,
        definition_source: str | None = None,
        locale: str | None = None,
    ) -> ExamPreparationStatus:
        self._emit("exam_start_progress_validating", locale)
        context = self.services.context
        project_path = resolve_active_project_path(context, self.services.config)
        readiness = ProjectPreflight(env=self._env).check(project_path)
        project_blockers = tuple(issue.code for issue in readiness.issues)
        project_ready = readiness.ready
        toolchain_preparation: ToolchainPreparationResult | None = None
        toolchain_blockers: tuple[str, ...] = ()
        if project_ready and readiness.project_path:
            self._emit("exam_start_progress_toolchain", locale)
            try:
                toolchain_preparation = self.toolchain.prepare(readiness.project_path)
            except Exception as exc:  # noqa: BLE001 - surfaced as a blocker
                toolchain_blockers = (
                    f"toolchain preparation failed: {type(exc).__name__}: {exc}",
                )
            else:
                toolchain_blockers = tuple(toolchain_preparation.blockers)
        toolchain_ready = (
            toolchain_preparation is not None and toolchain_preparation.ready
        )

        exam_definition_path = context.exam_definition_path
        instructions_path = exam_definition_path or context.instructions_path
        definition, exam_definition_blockers = self._definition(
            exam_definition_path or definition_source
            if require_exam_definition
            else None,
            required=require_exam_definition,
        )
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
        instructions_ready = True
        exam_definition_ready = (
            definition is not None and not exam_definition_blockers
        ) or not require_exam_definition
        return ExamPreparationStatus(
            student_ready=student_ready,
            project_path=readiness.project_path or project_path,
            project_ready=project_ready,
            project_blockers=project_blockers,
            instructions_path=instructions_path,
            instructions_ready=instructions_ready,
            instruction_blockers=(),
            active_exam=active is not None,
            ready_to_start=(
                student_ready
                and project_ready
                and instructions_ready
                and exam_definition_ready
                and active is None
                and toolchain_ready
            ),
            exam_definition_path=exam_definition_path,
            exam_definition_ready=exam_definition_ready,
            exam_definition_blockers=exam_definition_blockers,
            definition=definition,
            toolchain_ready=toolchain_ready,
            toolchain_blockers=toolchain_blockers,
            toolchain_preparation=toolchain_preparation,
        )

    def _emit(self, key: str, locale: str | None) -> None:
        if self._progress is not None:
            self._progress(get_ui_string(key, locale))

    def _definition(
        self, configured: str | None, *, required: bool = True
    ) -> tuple[ExamDefinition | None, tuple[str, ...]]:
        if not configured:
            return (None, ("no_exam_definition",) if required else ())
        if configured.strip().startswith("{"):
            try:
                return self.loader.load_text(configured, exam_id=None), ()
            except ExamDefinitionValidationError:
                return None, ("exam_definition_invalid",)
        try:
            resolved = ResourceResolver(self._base_dir).resolve(
                configured, ResourceKind.EXAM_DEFINITION
            )
        except ResourcePathError as exc:
            return None, (self._definition_blocker(exc),)
        try:
            return self.loader.load(resolved, exam_id=None), ()
        except ExamDefinitionValidationError as exc:
            reason = str(exc)
            if "instructions" in reason:
                return None, ("exam_definition_wrong_resource",)
            return None, ("exam_definition_invalid",)

    @staticmethod
    def _definition_blocker(error: ResourcePathError) -> str:
        reason = error.reason.lower()
        if "does not exist" in reason:
            return "exam_definition_missing"
        if "permission" in reason or "read" in reason or "utf-8" in reason:
            return "exam_definition_unreadable"
        return "exam_definition_invalid"


__all__ = ["ExamPreparationService", "ExamPreparationStatus"]
