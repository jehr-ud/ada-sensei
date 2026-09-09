from __future__ import annotations

from ada_sensei.config import Secrets


def test_env_only(clean_env, monkeypatch):
    monkeypatch.setenv("ADA_SENSEI_API_KEY", "topsecret")
    secrets = Secrets(
        env=dict(clean_env), defaults={"api_key_env": "ADA_SENSEI_API_KEY"}
    )
    assert secrets.get("api_key_env") == "topsecret"

    assert (
        Secrets(env={}, defaults={"api_key_env": "ADA_SENSEI_API_KEY"}).get(
            "api_key_env"
        )
        is None
    )


def test_redact(clean_env, monkeypatch):
    monkeypatch.setenv("ADA_SENSEI_API_KEY", "topsecret")
    secrets = Secrets(
        env=dict(clean_env), defaults={"api_key_env": "ADA_SENSEI_API_KEY"}
    )
    assert secrets.redact("key is topsecret here") == "key is *** here"
