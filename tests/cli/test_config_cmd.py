from __future__ import annotations

from ada_sensei.cli.config_cmd import ConfigInitCommand
from ada_sensei.config import ConfigLoader


def test_init_template(tmp_path):
    target = tmp_path / "cfg" / "config.toml"
    path = ConfigInitCommand.config_init(target)
    assert path.exists()
    text = path.read_text()
    assert "ADA_SENSEI_API_KEY" in text or "api_key_env" in text
    assert "sk-" not in text


def test_init_writes_redacted_placeholders(tmp_path):
    target = tmp_path / "cfg"
    path = ConfigInitCommand.config_init(target)
    assert path == target / "config.toml"
    assert path.exists()


def test_project_path_override(tmp_path, clean_env):
    import os

    cfg = tmp_path / "c"
    ConfigInitCommand.config_init(cfg)
    env = dict(os.environ)
    env["ADA_SENSEI_CONFIG"] = str(cfg / "config.toml")
    loaded = ConfigLoader(env=env).load(config_file=str(cfg / "config.toml"))
    assert loaded.project.path == "."


def test_model_override(tmp_path):
    cfg = tmp_path / "c"
    path = ConfigInitCommand.config_init(cfg)
    existing = path.read_text()
    path.write_text(
        existing.replace('model = "qwen2.5-coder:7b"', 'model = "custom-model"'),
        encoding="utf-8",
    )
    loaded = ConfigLoader().load(config_file=str(path))
    assert loaded.llm.model == "custom-model"


def test_env_override_docs_no_secrets():
    docs = ConfigInitCommand.env_override_docs()
    assert "ADA_SENSEI_" in docs
    assert "sk-" not in docs