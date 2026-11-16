"""Best-effort opening of a generated file in the OS default viewer.

A presentation convenience for the TUI (RQ-EXM-049): opening the exam report
must never affect the exam result, so failures are reported as ``False`` and
never raised. The command is fixed per platform; no user input reaches it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _command(target: Path) -> list[str]:
    if sys.platform == "darwin":
        return ["open", str(target)]
    if sys.platform.startswith("win"):
        return ["cmd", "/c", "start", "", str(target)]
    return ["xdg-open", str(target)]


def open_path(path: str | Path) -> bool:
    """Open ``path`` with the platform viewer; return whether it was launched.

    Returns ``False`` when the file does not exist or no opener could be
    started. Never raises: callers treat this as best-effort.
    """
    target = Path(path)
    if not target.exists():
        return False
    try:
        subprocess.Popen(
            _command(target),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, ValueError):
        return False
    return True


__all__ = ["open_path"]
