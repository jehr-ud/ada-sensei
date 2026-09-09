from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def mini_config_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "pyproject.toml")


@pytest.fixture
def sample_config(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        """
[project]
path = "."

[llm]
provider = "ollama"
model = "file-model"
base_url = "http://localhost:11434/v1"
temperature = 0.2
timeout_seconds = 120
max_output_tokens = 2048
max_context_tokens = 8192
max_attempts = 3

[tools]
timeout_seconds = 600
network = true
offline = false
static_kotlin = "detekt"
static_android = "lint"

[secrets]
api_key_env = "ADA_SENSEI_API_KEY"
""",
        encoding="utf-8",
    )
    return config


@pytest.fixture
def clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("ADA_SENSEI_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    return os.environ
