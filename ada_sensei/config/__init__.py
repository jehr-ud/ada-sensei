from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .paths import PathResolver

ENV_PREFIX = "ADA_SENSEI_"

ENV_KEYS: dict[str, str] = {
    "PROJECT_PATH": "project.path",
    "LLM_PROVIDER": "llm.provider",
    "LLM_MODEL": "llm.model",
    "LLM_BASE_URL": "llm.base_url",
    "LLM_TEMPERATURE": "llm.temperature",
    "LLM_TIMEOUT_SECONDS": "llm.timeout_seconds",
    "LLM_MAX_OUTPUT_TOKENS": "llm.max_output_tokens",
    "LLM_MAX_CONTEXT_TOKENS": "llm.max_context_tokens",
    "LLM_MAX_ATTEMPTS": "llm.max_attempts",
    "LLM_CONTEXT_CONVERSATION_BUDGET": "llm.context.conversation_budget",
    "LLM_CONTEXT_EVIDENCE_BUDGET": "llm.context.evidence_budget",
    "TOOLS_TIMEOUT_SECONDS": "tools.timeout_seconds",
    "TOOLS_NETWORK": "tools.network",
    "TOOLS_OFFLINE": "tools.offline",
    "TOOLS_STATIC_KOTLIN": "tools.static_kotlin",
    "TOOLS_STATIC_ANDROID": "tools.static_android",
    "SECRETS_API_KEY_ENV": "secrets.api_key_env",
}


class ProjectConfig(BaseModel):
    path: str = "."


class LLMContextConfig(BaseModel):
    conversation_budget: float = 0.4
    evidence_budget: float = 0.4

    @field_validator("conversation_budget", "evidence_budget")
    @classmethod
    def _valid_shares(cls, value: float) -> float:
        if not 0.0 < value <= 1.0:
            raise ValueError("budget share must be in (0, 1]")
        return value


class LLMConfig(BaseModel):
    provider: str = "ollama"
    model: str = "qwen2.5-coder:7b"
    base_url: str = "http://localhost:11434/v1"
    temperature: float = 0.2
    timeout_seconds: int = 120
    max_output_tokens: int = 2048
    max_context_tokens: int = 8192
    max_attempts: int = 3
    context: LLMContextConfig = LLMContextConfig()

    @field_validator("max_attempts")
    @classmethod
    def _max_attempts_within_rules(cls, value: int) -> int:
        if not 1 <= value <= 3:
            raise ValueError(
                "max_attempts must be between 1 and 3 "
                "(1 initial attempt + up to 2 retries)"
            )
        return value


class ToolsConfig(BaseModel):
    timeout_seconds: int = 600
    network: bool = True
    offline: bool = False
    static_kotlin: str = "detekt"
    static_android: str = "lint"


class StorageConfig(BaseModel):
    data_dir: str | None = None
    config_dir: str | None = None
    cache_dir: str | None = None


class SecretsConfig(BaseModel):
    api_key_env: str = "ADA_SENSEI_API_KEY"


class Config(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    data_dir: Path | None = None
    config_file: Path | None = None
    cache_dir: Path | None = None

    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir or Path(os.path.expandvars(self.storage.data_dir or ""))


class _ConfigBuilder(BaseModel):
    project: dict[str, Any] = Field(default_factory=dict)
    llm: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)
    storage: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)


class ConfigLoader:
    def __init__(
        self, env: dict[str, str] | None = None, cwd: Path | None = None
    ) -> None:
        self._env = env if env is not None else os.environ
        self._cwd = (cwd or Path.cwd()).resolve()

    @staticmethod
    def _set_dotted(target: dict[str, Any], dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        node = target
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    @staticmethod
    def _coerce(value: Any, current: Any) -> Any:
        if isinstance(current, bool):
            return str(value).strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(current, int):
            return int(value)
        if isinstance(current, float):
            return float(value)
        return value

    def load(
        self,
        config_file: str | Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> Config:
        data: dict[str, Any] = {
            "project": {},
            "llm": {},
            "tools": {},
            "storage": {},
            "secrets": {},
        }
        paths = PathResolver.resolved(self._env)
        file_path = Path(config_file) if config_file else paths.config_file

        if file_path.exists():
            with file_path.open("rb") as fh:
                raw = tomllib.load(fh)
            for key in ("project", "llm", "tools", "storage", "secrets"):
                data[key].update(raw.get(key, {}))
        else:
            file_path = paths.config_file

        for suffix, dotted in ENV_KEYS.items():
            raw = self._env.get(f"{ENV_PREFIX}{suffix}")
            if raw is None:
                continue
            node = data
            for part in dotted.split(".")[:-1]:
                node = node.setdefault(part, {})
            key = dotted.split(".")[-1]
            node[key] = self._coerce(raw, node.get(key))

        if cli_overrides:
            for dotted, value in cli_overrides.items():
                self._set_dotted(data, dotted, value)

        builder = _ConfigBuilder.model_validate(data)
        merged = Config(
            project=ProjectConfig(**builder.project),
            llm=LLMConfig(**builder.llm),
            tools=ToolsConfig(**builder.tools),
            storage=StorageConfig(**builder.storage),
            secrets=SecretsConfig(**builder.secrets),
        )

        merged.data_dir = Path(
            os.path.expandvars(builder.storage.get("data_dir") or str(paths.data_dir))
        )
        merged.cache_dir = Path(
            os.path.expandvars(builder.storage.get("cache_dir") or str(paths.cache_dir))
        )
        cfg_file_override = builder.storage.get("config_dir")
        if cfg_file_override:
            merged.config_file = (
                Path(os.path.expandvars(cfg_file_override)) / "config.toml"
            )
        else:
            merged.config_file = file_path
        return merged


class Secrets:
    def __init__(
        self, env: dict[str, str] | None = None, defaults: dict[str, str] | None = None
    ) -> None:
        self._env = env if env is not None else os.environ
        self._defaults = defaults or {}

    @classmethod
    def from_config(cls, config: Config, env: dict[str, str] | None = None) -> Secrets:
        return cls(env=env, defaults={"api_key_env": config.secrets.api_key_env})

    def get(self, name: str) -> str | None:
        key = self._defaults.get(name, name)
        return self._env.get(key)

    def all(self) -> dict[str, str]:
        return {
            name: value
            for name in self._defaults
            if (value := self._env.get(self._defaults[name]))
        }

    def redact(self, text: str) -> str:
        for value in self.all().values():
            if value and value in text:
                text = text.replace(value, "***")
        return text
