"""Centralized cross-platform resolution of ADA Sensei file resources."""

from __future__ import annotations

import os
import re
from enum import StrEnum
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel

_FOREIGN_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]|^\\\\")

_TITLES: dict[str, str] = {
    "instructions": "Instructions resource error",
    "exam_definition": "Exam definition error",
    "project_workspace": "Project workspace error",
    "learning_path": "Learning path resource error",
    "toolchain_policy": "Toolchain policy error",
}


class ResourceKind(StrEnum):
    INSTRUCTIONS = "instructions"
    EXAM_DEFINITION = "exam_definition"
    PROJECT_WORKSPACE = "project_workspace"
    LEARNING_PATH = "learning_path"
    TOOLCHAIN_POLICY = "toolchain_policy"


class ResourceReference(BaseModel):
    """Persisted pointer to a user or package resource."""

    value: str = ""
    base: str | None = None
    package: str | None = None
    resource: str | None = None


class ResourcePathError(Exception):
    """A configured resource cannot be resolved or used."""

    def __init__(
        self,
        resource: ResourceKind | str,
        path: str | Path,
        reason: str,
    ) -> None:
        self.resource = str(resource)
        self.path = str(path)
        self.reason = reason
        super().__init__(self.render())

    def render(self) -> str:
        title = _TITLES.get(self.resource, "Resource path error")
        return (
            f"{title}\n"
            f"Resource: {self.resource}\n"
            f"Resolved path: {self.path}\n"
            f"Reason: {self.reason}"
        )


class ResourceResolver:
    """Resolve user-supplied and packaged resources without using cwd guesses."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = (
            Path(base_dir).expanduser().resolve() if base_dir is not None else None
        )

    def resolve(
        self,
        value: str | Path,
        resource: ResourceKind | str,
        *,
        base_dir: str | Path | None = None,
        expect_directory: bool = False,
        check_readable: bool = True,
    ) -> Path:
        raw = str(value).strip()
        if not raw:
            raise ResourcePathError(resource, raw, "path is empty")
        if _FOREIGN_ABSOLUTE.match(raw):
            raise ResourcePathError(
                resource, raw, "path uses another operating system's absolute format"
            )
        candidate = Path(raw).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve(strict=False)
        else:
            base = self._base_dir(base_dir, resource, raw)
            resolved = (base / candidate).resolve(strict=False)
        self._validate(resolved, resource, expect_directory, check_readable)
        return resolved

    def resolve_reference(
        self,
        reference: str | Path | ResourceReference | None,
        resource: ResourceKind | str,
        *,
        base_dir: str | Path | None = None,
        expect_directory: bool = False,
    ) -> Path:
        if reference is None:
            raise ResourcePathError(resource, "<not configured>", "path is empty")
        if isinstance(reference, ResourceReference) and reference.package:
            return self.resolve_package(
                reference.package,
                reference.resource or "",
                resource,
            )
        if isinstance(reference, ResourceReference):
            value = reference.value
            saved_base = reference.base
        else:
            value = str(reference)
            saved_base = None
        candidate = Path(value).expanduser()
        is_relative = not candidate.is_absolute() and not _FOREIGN_ABSOLUTE.match(value)
        if saved_base and is_relative:
            base_path = Path(saved_base).expanduser()
            if not base_path.is_dir():
                raise ResourcePathError(
                    resource,
                    (base_path / candidate).resolve(strict=False),
                    "saved base directory is not available on this system",
                )
            return self.resolve(
                value,
                resource,
                base_dir=base_path,
                expect_directory=expect_directory,
            )
        return self.resolve(
            value,
            resource,
            base_dir=base_dir,
            expect_directory=expect_directory,
        )

    def resolve_package(
        self,
        package: str,
        resource_path: str,
        resource: ResourceKind | str,
    ) -> Path:
        label = f"{package}:{resource_path}"
        node: Any = files(package)
        for part in PurePosixPath(resource_path).parts:
            node = node.joinpath(part)
        if not node.is_file():
            raise ResourcePathError(resource, label, "package resource does not exist")
        try:
            path = Path(str(node))
        except TypeError as exc:
            raise ResourcePathError(
                resource, label, "package resource is not a filesystem file"
            ) from exc
        if not os.access(path, os.R_OK):
            raise ResourcePathError(resource, label, "permission denied")
        return path

    def reference_for(
        self,
        value: str | Path,
        resource: ResourceKind | str,
        *,
        base_dir: str | Path | None = None,
        package: str | None = None,
        resource_path: str | None = None,
    ) -> ResourceReference:
        if package is not None:
            return ResourceReference(
                value="", package=package, resource=resource_path or ""
            )
        path = self.resolve(value, resource, base_dir=base_dir)
        base = self._base_dir(base_dir, resource, str(value))
        try:
            relative = path.relative_to(base)
        except ValueError:
            return ResourceReference(value=str(path))
        return ResourceReference(value=relative.as_posix(), base=str(base))

    def _base_dir(
        self,
        base_dir: str | Path | None,
        resource: ResourceKind | str,
        raw: str,
    ) -> Path:
        base = Path(base_dir).expanduser().resolve() if base_dir else self.base_dir
        if base is None:
            raise ResourcePathError(
                resource,
                raw,
                "relative path requires an explicitly configured base directory",
            )
        return base

    @staticmethod
    def _validate(
        path: Path,
        resource: ResourceKind | str,
        expect_directory: bool,
        check_readable: bool,
    ) -> None:
        if not path.exists():
            reason = (
                "directory does not exist"
                if expect_directory
                else "file does not exist"
            )
            raise ResourcePathError(resource, path, reason)
        if expect_directory:
            if not path.is_dir():
                raise ResourcePathError(resource, path, "path is not a directory")
        elif not path.is_file():
            raise ResourcePathError(resource, path, "path is not a regular file")
        if check_readable and not os.access(path, os.R_OK):
            raise ResourcePathError(resource, path, "permission denied")


__all__ = [
    "ResourceKind",
    "ResourcePathError",
    "ResourceReference",
    "ResourceResolver",
]
