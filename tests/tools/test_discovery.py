from __future__ import annotations

import pytest
from ada_sensei.tools import ToolDiscovery, ToolUnavailable


def test_missing_reported(tmp_path, clean_env, monkeypatch):
    wrapper = tmp_path / "gradlew"
    wrapper.write_text("#!/bin/sh\n")
    wrapper.chmod(0o755)
    gradle = ToolDiscovery.find_gradle(tmp_path, env=dict(clean_env))
    assert gradle.available
    assert gradle.command == str(wrapper)

    missing = ToolDiscovery.find_gradle(
        tmp_path / "does-not-exist", env=dict(clean_env)
    )
    assert not missing.available


def test_tool_unavailable_raised():
    with pytest.raises(ToolUnavailable):
        raise ToolUnavailable("missing tool")


def test_discover_returns_entries(tmp_path, clean_env, monkeypatch):
    (tmp_path / "gradlew").write_text("#!/bin/sh\n")
    tools = ToolDiscovery.discover(tmp_path, env=dict(clean_env))
    assert set(tools) == {"gradle", "jdk", "android-sdk"}
    assert tools["gradle"].available


def test_jdk_and_sdk_fields_exist(clean_env):
    jdk = ToolDiscovery.find_jdk(env=dict(clean_env))
    assert hasattr(jdk, "available")
    sdk = ToolDiscovery.find_sdk(env=dict(clean_env))
    assert hasattr(sdk, "available")
    assert hasattr(sdk, "command")
