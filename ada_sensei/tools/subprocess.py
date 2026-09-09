from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..models import Evidence


@dataclass
class SubprocessResult:
    command: list[str]
    cwd: str | None
    exit_code: int | None
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    command_error: str = ""

    @property
    def status(self) -> str:
        if self.timed_out:
            return "missing"
        if self.command_error:
            return "missing"
        return "pass" if self.exit_code == 0 else "fail"

    def to_evidence(
        self, source: str, type: str, severity: str | None = None
    ) -> Evidence:
        return Evidence(
            source=source,
            type=type,
            severity=severity,
            status=self.status,
            message=(self.stdout or self.stderr)[-4000:],
            command=" ".join(self.command),
        )


class SubprocessRunner:
    def __init__(
        self,
        *,
        timeout_seconds: int = 600,
        offline: bool = False,
        redactor: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.offline = offline
        self.redactor = redactor or (lambda text: text)
        self._env = env if env is not None else os.environ.copy()

    def run(
        self,
        cmd: list[str],
        *,
        cwd: str | Path | None = None,
        timeout: int | None = None,
    ) -> SubprocessResult:
        started = time.monotonic()
        cwd_str = str(cwd.resolve()) if cwd else None
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout_seconds,
                cwd=cwd_str,
                env=self._env,
            )
            exit_code = proc.returncode
            stdout = self.redactor(proc.stdout)
            stderr = self.redactor(proc.stderr)
            err = ""
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            exit_code = None
            stdout = ""
            stderr = self.redactor(str(exc))
            err = "timeout"
            timed_out = True
        except FileNotFoundError as exc:
            exit_code = None
            stdout = ""
            stderr = self.redactor(str(exc))
            err = f"command not found: {exc}"
            timed_out = False
        duration = time.monotonic() - started
        return SubprocessResult(
            command=cmd,
            cwd=cwd_str,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_s=duration,
            timed_out=timed_out,
            command_error=err,
        )
