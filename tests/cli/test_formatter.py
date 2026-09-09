from __future__ import annotations

from ada_sensei.cli.formatter import Formatter
from ada_sensei.config import Secrets


def test_secret_redacted():
    secrets = Secrets(
        env={"ADA_SENSEI_API_KEY": "SUPERSECRET"},
        defaults={"api_key_env": "ADA_SENSEI_API_KEY"},
    )
    formatter = Formatter(secrets)
    out = formatter.error("authorization failed: endpoint used SUPERSECRET token")
    assert "SUPERSECRET" not in out
    assert "***" in out


def test_redact_no_secrets_noop():
    secrets = Secrets(env={}, defaults={"api_key_env": "ADA_SENSEI_API_KEY"})
    formatter = Formatter(secrets)
    assert formatter.error("plain message") == "plain message"


def test_sanitized_uses_type_name():
    formatter = Formatter()
    assert "ValueError" in formatter.sanitized(ValueError("boom"))
    assert "boom" in formatter.sanitized(ValueError("boom"))