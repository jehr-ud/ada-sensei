from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_requires():
    with (ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    requires = data["project"]["requires-python"]
    assert requires == ">=3.11,<4.0"
    scripts = data["project"]["scripts"]
    assert scripts["ada-sensei"] == "ada_sensei.cli.app:CLIApp.main"


def test_github_install():
    with (ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    urls = data.get("project", {}).get("urls", {})
    assert urls.get("repository", "").startswith(
        "https://github.com/jehr-ud/ada-sensei"
    )

    readme = (ROOT / "README.md").read_text()
    assert "pip install git+https://github.com/jehr-ud/ada-sensei.git" in readme


def test_runtime_doc_exists():
    assert (ROOT / "docs" / "runtime.md").exists()
    assert "qwen2.5-coder:7b" in (ROOT / "docs" / "runtime.md").read_text()
