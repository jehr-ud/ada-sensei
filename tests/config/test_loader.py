from __future__ import annotations

import pytest
from ada_sensei.config import ConfigLoader


def test_precedence(tmp_path, clean_env, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[llm]\nmodel = "file-model"\n')
    monkeypatch.setenv("ADA_SENSEI_LLM_MODEL", "env-model")

    loaded = ConfigLoader(env=dict(clean_env)).load(config_file=config_file)
    assert loaded.llm.model == "env-model"

    loaded = ConfigLoader(env=dict(clean_env)).load(
        config_file=config_file, cli_overrides={"llm.model": "cli-model"}
    )
    assert loaded.llm.model == "cli-model"


def test_defaults(clean_env):
    loaded = ConfigLoader(env=dict(clean_env)).load()
    assert loaded.llm.provider == "ollama"
    assert loaded.llm.model == "qwen2.5-coder:7b"
    assert loaded.llm.max_attempts == 3
    assert loaded.tools.timeout_seconds == 600
    assert not loaded.tools.offline


def test_project_path(tmp_path, clean_env, monkeypatch):
    from ada_sensei.config import ConfigLoader

    monkeypatch.setenv("ADA_SENSEI_PROJECT_PATH", str(tmp_path))
    loaded = ConfigLoader(env=dict(clean_env)).load()
    assert loaded.project.path == str(tmp_path)

    loaded = ConfigLoader(env=dict(clean_env)).load(
        cli_overrides={"project.path": "/cli/project"}
    )
    assert loaded.project.path == "/cli/project"


def test_llm_settings(sample_config, clean_env):
    from ada_sensei.config import ConfigLoader

    loaded = ConfigLoader(env=dict(clean_env)).load(config_file=sample_config)
    assert loaded.llm.model == "file-model"
    assert loaded.llm.base_url == "http://localhost:11434/v1"
    assert loaded.llm.max_context_tokens == 8192


def test_max_attempts_invalid(clean_env, monkeypatch):
    from ada_sensei.config import ConfigLoader

    monkeypatch.setenv("ADA_SENSEI_LLM_MAX_ATTEMPTS", "5")
    with pytest.raises(ValueError):
        ConfigLoader(env=dict(clean_env)).load()
