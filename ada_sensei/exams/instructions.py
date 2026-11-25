"""Loader for teacher-authored Markdown exam instructions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..resources.paths import (
    ResourceKind,
    ResourcePathError,
    ResourceResolver,
)

_EXAM_DEFINITION_MARKERS = frozenset(
    {"schema_version", "exam_id", "requirements", "rubric_ref"}
)
_INSTRUCTIONS_PACKAGE = "ada_sensei.resources"


@dataclass(frozen=True)
class InstructionsDocument:
    """Validated, read-only instructions content."""

    path: Path
    text: str
    source: str


class InstructionsLoader:
    """Load instructions without ever interpreting an exam definition as text."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._resolver = ResourceResolver(base_dir)

    def load(
        self,
        source: str | Path,
        *,
        base_dir: str | Path | None = None,
    ) -> InstructionsDocument:
        path = self._resolver.resolve(
            source, ResourceKind.INSTRUCTIONS, base_dir=base_dir
        )
        return self._load_path(path)

    def load_package(self, locale: str = "en-US") -> InstructionsDocument:
        suffix = "es" if str(locale).startswith("es") else "en"
        resource = f"instructions/default.{suffix}.md"
        path = self._resolver.resolve_package(
            _INSTRUCTIONS_PACKAGE, resource, ResourceKind.INSTRUCTIONS
        )
        document = self._load_path(path)
        return InstructionsDocument(
            path=path,
            text=document.text,
            source=f"{_INSTRUCTIONS_PACKAGE}:{resource}",
        )

    def _load_path(self, path: Path) -> InstructionsDocument:
        if path.suffix.lower() == ".json":
            raise ResourcePathError(
                ResourceKind.INSTRUCTIONS,
                path,
                "exam definition JSON cannot be used as instructions; "
                "configure it with /instructions <path>",
            )
        if path.suffix.lower() != ".md":
            raise ResourcePathError(
                ResourceKind.INSTRUCTIONS,
                path,
                "instructions must be a Markdown (.md) file",
            )
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            raise ResourcePathError(
                ResourceKind.INSTRUCTIONS, path, "file is not valid UTF-8"
            ) from exc
        except OSError as exc:
            raise ResourcePathError(
                ResourceKind.INSTRUCTIONS, path, f"file could not be read: {exc}"
            ) from exc
        self._validate_content(text, path)
        return InstructionsDocument(path=path, text=text, source=str(path))

    @staticmethod
    def _validate_content(text: str, path: Path) -> None:
        if not text.strip():
            raise ResourcePathError(
                ResourceKind.INSTRUCTIONS, path, "instructions file is empty"
            )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return
        if isinstance(payload, dict) and _EXAM_DEFINITION_MARKERS.issubset(payload):
            raise ResourcePathError(
                ResourceKind.INSTRUCTIONS,
                path,
                "exam definition JSON cannot be used as instructions; "
                "configure it with /instructions <path>",
            )
        raise ResourcePathError(
            ResourceKind.INSTRUCTIONS,
            path,
            "instructions must be Markdown text, not a JSON object",
        )


__all__ = ["InstructionsDocument", "InstructionsLoader"]
