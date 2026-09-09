"""Dependency isolation (RQ-TUI-027).

Textual-specific imports must be confined to the TUI package. Core/domain,
action, LLM, persistence, and Android analysis packages must remain independent.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "ada_sensei"

FORBIDDEN = frozenset(
    {
        "cli/tui",  # the only allowed textual home
    }
)

NON_TUI_PACKAGES = (
    "actions",
    "config",
    "context.py",
    "llm",
    "models.py",
    "storage",
    "tools",
    "urns.py",
    "setup",
)


def test_textual_imports_confined_to_tui():
    offenders: list[str] = []
    for py in ROOT.rglob("*.py"):
        rel = py.relative_to(ROOT).as_posix()
        if rel.startswith("cli/tui"):
            continue
        text = py.read_text(encoding="utf-8")
        if "import textual" in text or "from textual" in text:
            offenders.append(rel)
    assert offenders == [], f"non-TUI modules import textual: {offenders}"


def test_non_tui_packages_do_not_import_textual():
    for pkg in NON_TUI_PACKAGES:
        target = ROOT / pkg
        files = [target] if target.is_file() else list(target.rglob("*.py")) if target.exists() else []
        for py in files:
            text = py.read_text(encoding="utf-8")
            assert "textual" not in text, f"{py.relative_to(ROOT)} imports textual"
