"""Authoritative ADA Sensei application version.

Single source of truth for the running build version displayed in the GUI
header/footer. Prefers installed package metadata, falls back to the
``__version__`` constant (which mirrors ``pyproject.toml``) so development
checkouts without installed metadata still render a version instead of
crashing. Never requires an LLM request.
"""

from __future__ import annotations

import contextlib
from importlib import metadata

__version__ = "0.1.0"


def get_app_version() -> str:
    """Return the installed application version, never raising.

    Prefers ``importlib.metadata`` (installed build metadata). Falls back to
    :data:`__version__`. Returns ``"unknown"`` only when both are unavailable.
    """
    with contextlib.suppress(Exception):
        found = metadata.version("ada-sensei")
        if found:
            return found
    try:
        return __version__
    except Exception:  # noqa: BLE001 - version must never crash the GUI
        return "unknown"


__all__ = ["__version__", "get_app_version"]
