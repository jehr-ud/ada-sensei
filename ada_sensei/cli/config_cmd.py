from __future__ import annotations

import os
from pathlib import Path

from ..config import ENV_KEYS, ENV_PREFIX
from ..config.paths import PathResolver

DEFAULT_TEMPLATE = """\
# ADA Sensei configuration
# Edit as needed. Secret placeholders below are never populated.

[project]
path = "."

[llm]
provider = "ollama"
model = "qwen2.5-coder:7b"
base_url = "http://localhost:11434/v1"
temperature = 0.2
timeout_seconds = 120
max_output_tokens = 2048
max_context_tokens = 8192
max_attempts = 3

[llm.context]
conversation_budget = 0.4
evidence_budget = 0.4

[tools]
timeout_seconds = 600
network = true
offline = false
static_kotlin = "detekt"
static_android = "lint"

[storage]
# Optional overrides; leave commented to use XDG defaults.
# data_dir = ""
# config_dir = ""
# cache_dir = ""

[secrets]
# The name of the environment variable holding the API key, if required.
api_key_env = "ADA_SENSEI_API_KEY"
"""


class ConfigInitCommand:
    @staticmethod
    def config_init(
        target: str | Path | None = None, env: dict[str, str] | None = None
    ) -> Path:
        """Write a default config template (secrets never populated).

        When `target` is provided it is written verbatim; otherwise the XDG config
        location is used.
        """
        if target:
            path = Path(target).expanduser()
            path = path if path.suffix == ".toml" else path / "config.toml"
        else:
            env = env if env is not None else os.environ
            path = PathResolver.config_home(env) / "ada-sensei" / "config.toml"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_TEMPLATE, encoding="utf-8")
        return path

    @staticmethod
    def env_override_docs() -> str:
        """Describe supported environment variables without revealing secrets."""
        lines = ["Environment overrides (ADA_SENSEI_*):"]
        for suffix, dotted in ENV_KEYS.items():
            lines.append(f"  {ENV_PREFIX}{suffix} -> {dotted}")
        return "\n".join(lines)