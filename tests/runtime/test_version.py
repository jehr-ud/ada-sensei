"""Application version source of truth (RQ-TUI-037)."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_version_matches_build_metadata():
    from ada_sensei.version import __version__, get_app_version

    with (ROOT / "pyproject.toml").open("rb") as fh:
        declared = tomllib.load(fh)["project"]["version"]
    assert __version__ == declared
    assert get_app_version() == declared


def test_version_is_not_schema_or_catalog_version():
    from ada_sensei.version import get_app_version

    assert get_app_version() != "1.0.0"  # stages schema_version
    assert get_app_version() != "1.2.0"  # catalog_version


def test_missing_metadata_degrades_gracefully(monkeypatch):
    import ada_sensei.version as ver

    monkeypatch.setattr(
        ver.metadata, "version", lambda _name: (_ for _ in ()).throw(Exception("no dist"))
    )
    assert ver.get_app_version() == ver.__version__


def test_router_exposes_version(tmp_path):
    from ada_sensei.cli.router import CommandRouter
    from ada_sensei.config import Config
    from ada_sensei.version import get_app_version

    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = CommandRouter(config=config, client=None)
    assert router.app_version() == get_app_version()
