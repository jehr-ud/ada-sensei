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


def test_sdk_dir_from_local_properties_is_literal_and_wins_over_env(
    tmp_path, monkeypatch
):
    value = r"C\:\\Users\\LENOVO\\AppData\\Local\\Android\\Sdk"
    (tmp_path / "local.properties").write_text(
        f"sdk.dir={value}\n", encoding="utf-8"
    )
    monkeypatch.setenv("ANDROID_HOME", str(tmp_path))

    sdk = ToolDiscovery.find_sdk(project=tmp_path)

    assert sdk.available
    assert sdk.command == value


def test_sdk_dir_from_local_properties_accepts_wsl_path(tmp_path):
    value = "/mnt/c/Users/LENOVO/AppData/Local/Android/Sdk"
    (tmp_path / "local.properties").write_text(
        f"sdk.dir={value}\n", encoding="utf-8"
    )

    sdk = ToolDiscovery.find_sdk(project=tmp_path)

    assert sdk.available
    assert sdk.command == value


def test_sdk_dir_from_local_properties_accepts_linux_path(tmp_path):
    value = "/home/usuario/Android/Sdk"
    (tmp_path / "local.properties").write_text(
        f"sdk.dir={value}\n", encoding="utf-8"
    )

    sdk = ToolDiscovery.find_sdk(project=tmp_path)

    assert sdk.available
    assert sdk.command == value


def test_sdk_falls_back_to_env_when_local_properties_has_no_sdk_dir(
    tmp_path, monkeypatch
):
    (tmp_path / "local.properties").write_text("# no sdk\n", encoding="utf-8")
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.setenv("ANDROID_SDK_ROOT", str(tmp_path))

    sdk = ToolDiscovery.find_sdk(project=tmp_path)

    assert sdk.available
    assert sdk.command == str(tmp_path)


def test_sdk_is_unavailable_without_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)

    sdk = ToolDiscovery.find_sdk(project=tmp_path)

    assert not sdk.available
    assert sdk.message == "Android SDK not found"
