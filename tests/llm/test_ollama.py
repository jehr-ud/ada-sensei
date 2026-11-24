from __future__ import annotations

from ada_sensei.config import ConfigLoader
from ada_sensei.llm.ollama import OllamaProvider


def test_default_url():
    provider = OllamaProvider()
    assert provider.base_url == "http://localhost:11434/v1"


def test_default_model_matches_config(tmp_path):
    config = ConfigLoader(env={}).load(config_file=tmp_path / "missing.toml")
    provider = OllamaProvider()

    assert config.llm.model == "qwen2.5-coder:7b"
    assert provider._payload([], None, None)["model"] == config.llm.model


def test_default_api_key_from_env(monkeypatch):
    monkeypatch.setenv("ADA_SENSEI_API_KEY", "secret")
    from ada_sensei.config import Secrets

    config = ConfigLoader().load()
    secrets = Secrets.from_config(config)
    provider = OllamaProvider(api_key=secrets.get("api_key_env"))
    assert provider.api_key == "secret"
