from __future__ import annotations

from ada_sensei.tools.subprocess import SubprocessRunner


def test_timeout_is_limitation():
    result = SubprocessRunner(timeout_seconds=1).run(["sleep", "10"], timeout=1)
    assert result.timed_out
    assert result.status == "missing"


def test_success():
    result = SubprocessRunner().run(["echo", "hello"])
    assert result.exit_code == 0
    assert result.status == "pass"


def test_failure():
    result = SubprocessRunner().run(["bash", "-c", "echo oops >&2; exit 3"])
    assert result.exit_code == 3
    assert result.status == "fail"


def test_command_not_found():
    result = SubprocessRunner().run(["definitely-not-a-command-xyz"])
    assert result.command_error
    assert result.status == "missing"


def test_redaction():
    from ada_sensei.config import Secrets

    secrets = Secrets(
        env={"ADA_SENSEI_API_KEY": "sekret"},
        defaults={"api_key_env": "ADA_SENSEI_API_KEY"},
    )
    runner = SubprocessRunner(redactor=secrets.redact)
    result = runner.run(["bash", "-c", "echo sekret"])
    assert "sekret" not in result.stdout
    assert "***" in result.stdout
