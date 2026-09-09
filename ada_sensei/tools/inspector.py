from __future__ import annotations

from pathlib import Path

SOURCE_SUFFIXES = {".kt", ".java"}


class ProjectInspector:
    def __init__(self, project_path: str | Path) -> None:
        self.project_root = Path(project_path).resolve()
        if not self.project_root.exists():
            raise FileNotFoundError(f"project does not exist: {self.project_root}")

    def structure(self, suffix: tuple[str, ...] = ()) -> list[str]:
        files: list[str] = []
        for path in sorted(self.project_root.rglob("*")):
            if any(
                part.startswith(".") or part in {"build", ".gradle"}
                for part in path.parts
            ):
                continue
            if path.is_file():
                if suffix and path.suffix not in suffix:
                    continue
                files.append(str(path.relative_to(self.project_root)))
        return files

    def list_source_files(self) -> list[str]:
        return self.structure(tuple(SOURCE_SUFFIXES))

    def read_file(self, relpath: str) -> str | None:
        target = self._safe_path(relpath)
        if not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None

    def exists(self, relpath: str) -> bool:
        return self._safe_path(relpath).exists()

    def has_gradle_wrapper(self) -> bool:
        return (self.project_root / "gradlew").is_file() or (
            self.project_root / "gradlew.bat"
        ).is_file()

    def _safe_path(self, relpath: str) -> Path:
        target = (self.project_root / relpath).resolve()
        if not target.is_relative_to(self.project_root):
            raise PermissionError(f"path escapes project root: {relpath}")
        return target
