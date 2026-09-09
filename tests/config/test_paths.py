from __future__ import annotations

from ada_sensei.config.paths import PathResolver


def test_xdg_layout(clean_env, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    paths = PathResolver.defaults(dict(clean_env))
    assert paths.data_dir == tmp_path / "data" / "ada-sensei"
    assert paths.config_file == tmp_path / "config" / "ada-sensei" / "config.toml"
    assert paths.cache_dir == tmp_path / "cache" / "ada-sensei"


def test_xdg_fallbacks(clean_env):
    env = dict(clean_env)
    env.pop("XDG_DATA_HOME", None)
    env.pop("XDG_CONFIG_HOME", None)
    env.pop("XDG_CACHE_HOME", None)
    paths = PathResolver.defaults(env)
    assert paths.data_dir.name == "ada-sensei"


def test_explicit_overrides(clean_env, monkeypatch):
    monkeypatch.setenv("ADA_SENSEI_DATA_DIR", "/overridden/data")
    monkeypatch.setenv("ADA_SENSEI_CONFIG", "/overridden/config.toml")
    monkeypatch.setenv("ADA_SENSEI_CACHE_DIR", "/overridden/cache")
    paths = PathResolver.resolved(dict(clean_env))
    assert str(paths.data_dir) == "/overridden/data"
    assert str(paths.config_file) == "/overridden/config.toml"
    assert str(paths.cache_dir) == "/overridden/cache"
