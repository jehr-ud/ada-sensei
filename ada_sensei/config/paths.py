from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

DATA_OVERRIDE = "ADA_SENSEI_DATA_DIR"
CONFIG_OVERRIDE = "ADA_SENSEI_CONFIG"
CACHE_OVERRIDE = "ADA_SENSEI_CACHE_DIR"


@dataclass(frozen=True)
class Paths:
    data_dir: Path
    config_file: Path
    cache_dir: Path

    def with_overrides(self, config_file: Path | None = None) -> Paths:
        return replace(self, config_file=config_file or self.config_file)


class PathResolver:
    @staticmethod
    def data_home(env: dict[str, str] | None = None) -> Path:
        env = env if env is not None else os.environ
        return Path(env.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")

    @staticmethod
    def config_home(env: dict[str, str] | None = None) -> Path:
        env = env if env is not None else os.environ
        return Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")

    @staticmethod
    def cache_home(env: dict[str, str] | None = None) -> Path:
        env = env if env is not None else os.environ
        return Path(env.get("XDG_CACHE_HOME") or Path.home() / ".cache")

    @staticmethod
    def defaults(env: dict[str, str] | None = None) -> Paths:
        env = env if env is not None else os.environ
        return Paths(
            data_dir=PathResolver.data_home(env) / "ada-sensei",
            config_file=PathResolver.config_home(env) / "ada-sensei" / "config.toml",
            cache_dir=PathResolver.cache_home(env) / "ada-sensei",
        )

    @staticmethod
    def resolved(env: dict[str, str] | None = None) -> Paths:
        env = env if env is not None else os.environ
        base = PathResolver.defaults(env)
        data_dir = Path(env[DATA_OVERRIDE]) if env.get(DATA_OVERRIDE) else base.data_dir
        config_file = (
            Path(env[CONFIG_OVERRIDE]) if env.get(CONFIG_OVERRIDE) else base.config_file
        )
        cache_dir = (
            Path(env[CACHE_OVERRIDE]) if env.get(CACHE_OVERRIDE) else base.cache_dir
        )
        return Paths(data_dir=data_dir, config_file=config_file, cache_dir=cache_dir)
