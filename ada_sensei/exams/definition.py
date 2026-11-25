"""JSON-only exam definition loading (RQ-EXM-052–063).

``exam-definition.schema.json`` is the single source of truth for the v1
teacher-authored JSON format. Markdown and PDF files are no longer authoritative
requirements sources: they may be attached as reading material, but the loader
only accepts a validated ``.json`` definition.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ..resources.paths import ResourceKind, ResourcePathError, ResourceResolver
from .models import (
    DEFAULT_EXAM_RUBRIC_REF,
    AcceptanceCriterion,
    DocumentationRules,
    ExamDefinition,
    ExamDefinitionError,
    RequirementSource,
    RequirementType,
    StatementFormat,
)

_SCHEMA_PATH = "schemas/exam-definition.schema.json"
_EXAM_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


@dataclass(frozen=True)
class ExamDefinitionIssue:
    """One actionable validation error tied to a JSON Pointer."""

    pointer: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.pointer}: {self.code}: {self.message}"


class ExamDefinitionValidationError(ExamDefinitionError):
    """A JSON definition failed syntax, schema, or semantic validation."""

    def __init__(self, issues: list[ExamDefinitionIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__(
            "invalid exam definition: " + "; ".join(issue.render() for issue in issues)
        )


class ExamDefinitionResourceError(ExamDefinitionValidationError):
    """A definition path cannot be resolved without confusing another resource."""

    def __init__(self, error: ResourcePathError) -> None:
        self.resource = error.resource
        self.path = error.path
        self.reason = error.reason
        self.issues = ()
        ExamDefinitionError.__init__(self, error.render())


class ExamDefinitionLoader:
    """Resolves a validated ``ExamDefinition`` from a teacher JSON file."""

    def load(
        self,
        source: str | Path,
        *,
        exam_id: str | None = None,
        base_dir: str | Path | None = None,
    ) -> ExamDefinition:
        resolver = ResourceResolver(base_dir)
        try:
            path = resolver.resolve(source, ResourceKind.EXAM_DEFINITION)
        except ResourcePathError as exc:
            if exc.reason == "file does not exist":
                raise ExamDefinitionValidationError(
                    [
                        ExamDefinitionIssue(
                            "/", "definition_not_found", str(exc)
                        )
                    ]
                ) from exc
            raise ExamDefinitionResourceError(exc) from exc
        if path.suffix.lower() != ".json":
            raise ExamDefinitionValidationError(
                [
                    ExamDefinitionIssue(
                        "/",
                        "unsupported_extension",
                        "only .json exam definitions are accepted",
                    )
                ]
            )
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ExamDefinitionResourceError(
                ResourcePathError(
                    ResourceKind.EXAM_DEFINITION,
                    path,
                    f"file could not be read: {exc}",
                )
            ) from exc
        return self._definition_from_json(
            raw, exam_id, str(path), str(path)
        )

    def load_text(
        self,
        text: str,
        *,
        statement_format: StatementFormat = StatementFormat.json,
        exam_id: str | None = None,
        source: str = "inline",
    ) -> ExamDefinition:
        """Normalize an inline JSON definition without touching the filesystem."""
        if statement_format is not StatementFormat.json:
            raise ExamDefinitionValidationError(
                [
                    ExamDefinitionIssue(
                        "/",
                        "unsupported_format",
                        "only JSON exam definitions are accepted",
                    )
                ]
            )
        return self._definition_from_json(text, exam_id, source, None)

    @staticmethod
    def _schema() -> dict[str, Any]:
        text = files("ada_sensei.exams").joinpath(_SCHEMA_PATH).read_text(
            encoding="utf-8"
        )
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ExamDefinitionError("bundled exam definition schema is invalid")
        return payload

    @classmethod
    def _parse_json(cls, raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExamDefinitionValidationError(
                [
                    ExamDefinitionIssue(
                        "/",
                        "invalid_json",
                        f"line {exc.lineno}, column {exc.colno}: {exc.msg}",
                    )
                ]
            ) from exc
        if not isinstance(payload, dict):
            raise ExamDefinitionValidationError(
                [
                    ExamDefinitionIssue(
                        "/", "invalid_root", "exam definition must be a JSON object"
                    )
                ]
            )
        return payload

    @classmethod
    def _definition_from_json(
        cls,
        raw: str,
        exam_id: str | None,
        source: str,
        source_path: str | None,
    ) -> ExamDefinition:
        payload = cls._parse_json(raw)
        issues = cls._validate(payload)
        if issues:
            raise ExamDefinitionValidationError(issues)
        definition = cls._build_definition(payload, raw, exam_id, source, source_path)
        try:
            return ExamDefinition.model_validate(definition)
        except ValueError as exc:
            raise ExamDefinitionValidationError(
                [ExamDefinitionIssue("/", "invalid_definition", str(exc))]
            ) from exc

    @classmethod
    def _validate(cls, payload: dict[str, Any]) -> list[ExamDefinitionIssue]:
        issues: list[ExamDefinitionIssue] = []
        validator = Draft202012Validator(cls._schema())
        for error in validator.iter_errors(payload):
            issues.append(cls._schema_issue(error))
        issues.extend(cls._validate_semantics(payload))
        return issues

    @staticmethod
    def _schema_issue(error: Any) -> ExamDefinitionIssue:
        pointer = ExamDefinitionLoader._pointer(error.absolute_path)
        code = str(error.validator or "schema_error")
        if error.validator == "required":
            match = re.search(r"'([^']+)' is a required property", error.message)
            if match:
                pointer = ExamDefinitionLoader._pointer(
                    list(error.absolute_path) + [match.group(1)]
                )
        return ExamDefinitionIssue(pointer, code, error.message)

    @staticmethod
    def _pointer(path: Any) -> str:
        parts = [str(part) for part in path]
        if not parts:
            return "/"
        escaped = [part.replace("~", "~0").replace("/", "~1") for part in parts]
        return "/" + "/".join(escaped)

    @staticmethod
    def _validate_semantics(payload: dict[str, Any]) -> list[ExamDefinitionIssue]:
        issues: list[ExamDefinitionIssue] = []
        requirements = payload.get("requirements")
        if not isinstance(requirements, list):
            return issues

        seen_requirements: dict[str, int] = {}
        seen_criteria: dict[str, str] = {}
        functional_weights: list[float] = []
        for index, raw_requirement in enumerate(requirements):
            if not isinstance(raw_requirement, dict):
                continue
            requirement_id = str(raw_requirement.get("id") or "")
            if requirement_id in seen_requirements:
                issues.append(
                    ExamDefinitionIssue(
                        f"/requirements/{index}/id",
                        "duplicate_id",
                        f"duplicate requirement id {requirement_id!r} "
                        f"(first used at index {seen_requirements[requirement_id]})",
                    )
                )
            else:
                seen_requirements[requirement_id] = index

            if raw_requirement.get("type") == "functional":
                try:
                    functional_weights.append(float(raw_requirement.get("weight")))
                except (TypeError, ValueError):
                    pass

            source = raw_requirement.get("source")
            if not isinstance(source, dict) or not source.get("file") or not source.get(
                "section"
            ):
                issues.append(
                    ExamDefinitionIssue(
                        f"/requirements/{index}/source",
                        "missing_source",
                        "source.file and source.section are required",
                    )
                )

            criteria = raw_requirement.get("acceptance_criteria")
            if not isinstance(criteria, list):
                continue
            for criterion_index, criterion in enumerate(criteria):
                if not isinstance(criterion, dict):
                    continue
                criterion_id = str(criterion.get("id") or "")
                previous = seen_criteria.get(criterion_id)
                pointer = (
                    f"/requirements/{index}/acceptance_criteria/{criterion_index}/id"
                )
                if previous is not None:
                    issues.append(
                        ExamDefinitionIssue(
                            pointer,
                            "duplicate_id",
                            f"duplicate acceptance criterion id {criterion_id!r} "
                            f"(first used by {previous})",
                        )
                    )
                else:
                    seen_criteria[criterion_id] = requirement_id
                verification = criterion.get("verification")
                if not isinstance(verification, list) or not verification:
                    issues.append(
                        ExamDefinitionIssue(
                            f"/requirements/{index}/acceptance_criteria/"
                            f"{criterion_index}/verification",
                            "missing_verification",
                            "at least one verification method is required",
                        )
                    )

        if functional_weights:
            total = sum(functional_weights)
            if abs(total - 1.0) > 1e-9:
                issues.append(
                    ExamDefinitionIssue(
                        "/requirements",
                        "invalid_functional_weights",
                        f"functional requirement weights must sum to 1.0, got {total}",
                    )
                )

        rubric_ref = payload.get("rubric_ref")
        if rubric_ref != DEFAULT_EXAM_RUBRIC_REF:
            issues.append(
                ExamDefinitionIssue(
                    "/rubric_ref",
                    "incompatible_rubric",
                    f"rubric_ref must be {DEFAULT_EXAM_RUBRIC_REF!r}",
                )
            )
        return issues

    @staticmethod
    def _build_definition(
        payload: dict[str, Any],
        raw: str,
        exam_id: str | None,
        source: str,
        source_path: str | None,
    ) -> dict[str, Any]:
        resolved_exam_id = str(exam_id or payload["exam_id"])
        if exam_id is None and not _EXAM_ID_RE.fullmatch(resolved_exam_id):
            raise ExamDefinitionValidationError(
                [
                    ExamDefinitionIssue(
                        "/exam_id",
                        "invalid_exam_id",
                        "exam_id must match ^[a-z0-9][a-z0-9-]{2,63}$",
                    )
                ]
            )
        return {
            "exam_id": resolved_exam_id,
            "schema_version": str(payload["schema_version"]),
            "title": str(payload["title"]),
            "version": str(payload["version"]),
            "description": str(payload.get("description") or ""),
            "statement_language": payload.get("statement_language"),
            "statement_format": StatementFormat.json,
            "statement_source": source,
            "original_statement": raw,
            "original_source_path": source_path,
            "definition_snapshot": raw,
            "definition_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "requirements": [
                ExamDefinitionLoader._build_requirement(item, index)
                for index, item in enumerate(payload["requirements"])
            ],
            "allowed_duration_seconds": _as_optional_int(
                payload.get("allowed_duration_seconds")
            ),
            "allowed_ask_count": _as_optional_int(payload.get("allowed_ask_count")),
            "rubric_ref": str(payload["rubric_ref"]),
            "documentation_rules": ExamDefinitionLoader._documentation_rules(
                payload.get("documentation_rules")
            ),
            "project_constraints": dict(payload.get("project_constraints") or {}),
            "limitations": [],
        }

    @staticmethod
    def _build_requirement(item: dict[str, Any], index: int) -> dict[str, Any]:
        requirement_type = RequirementType(str(item["type"]))
        dimension = (
            "functional_requirements"
            if requirement_type is RequirementType.functional
            else requirement_type.value
        )
        source = item.get("source")
        return {
            "requirement_id": str(item["id"]),
            "requirement_type": requirement_type,
            "title": str(item["title"]),
            "description": str(item["description"]),
            "dimension": dimension,
            "weight": float(item["weight"]),
            "source": (
                RequirementSource(
                    file=str(source["file"]),
                    section=str(source["section"]),
                    reference=(
                        str(source["reference"]) if source.get("reference") else None
                    ),
                )
                if isinstance(source, dict)
                else None
            ),
            "acceptance_criteria": [
                AcceptanceCriterion(
                    id=str(criterion["id"]),
                    description=str(criterion["description"]),
                    verification=list(criterion["verification"]),
                    evidence_hints=[
                        str(hint) for hint in (criterion.get("evidence_hints") or [])
                    ],
                )
                for criterion in item["acceptance_criteria"]
            ],
            "related_requirements": [
                str(value) for value in (item.get("related_requirements") or [])
            ],
            "tags": [str(value) for value in (item.get("tags") or [])],
            "evidence_expectations": [
                hint
                for criterion in item["acceptance_criteria"]
                for hint in (criterion.get("evidence_hints") or [])
            ],
        }

    @staticmethod
    def _documentation_rules(raw: object) -> DocumentationRules:
        if not isinstance(raw, dict):
            return DocumentationRules()
        defaults = DocumentationRules()
        return DocumentationRules(
            accepted_globs=tuple(raw.get("accepted_globs") or defaults.accepted_globs),
            required_files=tuple(raw.get("required_files") or ()),
            documentation_is_advisory=bool(
                raw.get(
                    "documentation_is_advisory",
                    defaults.documentation_is_advisory,
                )
            ),
        )


def _as_optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ExamDefinitionValidationError(
            [
                ExamDefinitionIssue(
                    "/", "invalid_limit", f"expected an integer limit, got {value!r}"
                )
            ]
        ) from exc


__all__ = [
    "ExamDefinitionIssue",
    "ExamDefinitionLoader",
    "ExamDefinitionResourceError",
    "ExamDefinitionValidationError",
]
