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


def _write_daemon_jvm(tmp_path, value):
    path = tmp_path / "gradle" / "gradle-daemon-jvm.properties"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"toolchainVersion={value}\n", encoding="utf-8")
    return path


def _java_env(tmp_path, major, minor=0):
    home = tmp_path / "java-home"
    java = home / "bin" / "java"
    java.parent.mkdir(parents=True, exist_ok=True)
    java.write_text("", encoding="utf-8")
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir(exist_ok=True)
    env = {"JAVA_HOME": str(home), "PATH": str(empty_path)}
    return env, str(java), (major, minor)


def test_gradle_daemon_jvm_version_is_recognized(tmp_path):
    properties = _write_daemon_jvm(tmp_path, "17")

    jvm = ToolDiscovery.find_gradle_jvm(tmp_path)

    assert jvm.available
    assert jvm.version == "17"
    assert jvm.command == str(properties)


def test_gradle_daemon_jvm_file_missing(tmp_path):
    jvm = ToolDiscovery.find_gradle_jvm(tmp_path)

    assert not jvm.available
    assert jvm.version is None


def test_gradle_daemon_jvm_invalid_value_is_not_invented(tmp_path, monkeypatch):
    _write_daemon_jvm(tmp_path, "unknown")
    env, java, version = _java_env(tmp_path, 17)
    monkeypatch.setattr(ToolDiscovery, "_java_version", lambda path: version)

    jvm = ToolDiscovery.find_gradle_jvm(tmp_path)
    jdk = ToolDiscovery.find_jdk(env=env, project=tmp_path)

    assert jvm.version is None
    assert not jvm.available
    assert jdk.available
    assert jdk.version == "17.0"
    assert jdk.command == java


def test_installed_jdk_wins_over_declared_gradle_jvm(tmp_path, monkeypatch):
    _write_daemon_jvm(tmp_path, "17")
    env, java, version = _java_env(tmp_path, 21)
    monkeypatch.setattr(ToolDiscovery, "_java_version", lambda path: version)

    jdk = ToolDiscovery.find_jdk(env=env, project=tmp_path)

    assert jdk.available
    assert jdk.version == "21.0"
    assert jdk.command == java
    assert "Gradle daemon JVM 17" in jdk.message


def test_declared_gradle_jvm_does_not_pretend_to_be_installed(tmp_path):
    properties = _write_daemon_jvm(tmp_path, "17")
    env = {"JAVA_HOME": "", "PATH": str(tmp_path / "empty-path")}
    (tmp_path / "empty-path").mkdir()

    jdk = ToolDiscovery.find_jdk(env=env, project=tmp_path)

    assert not jdk.available
    assert jdk.version == "17"
    assert jdk.command == str(properties)
    assert "no installed JDK" in jdk.message


def test_project_without_jdk_information_keeps_runtime_detection(
    tmp_path, monkeypatch
):
    env, java, version = _java_env(tmp_path, 17)
    monkeypatch.setattr(ToolDiscovery, "_java_version", lambda path: version)

    jdk = ToolDiscovery.find_jdk(env=env, project=tmp_path)

    assert jdk.available
    assert jdk.version == "17.0"
    assert jdk.command == java
    assert jdk.message == ""


def test_java_11_compile_target_is_not_runtime_jdk(tmp_path, monkeypatch):
    _write_daemon_jvm(tmp_path, "17")
    app = tmp_path / "app"
    app.mkdir()
    (app / "build.gradle.kts").write_text(
        "android { compileOptions { sourceCompatibility = "
        "JavaVersion.VERSION_11 } }\n",
        encoding="utf-8",
    )
    env, java, version = _java_env(tmp_path, 17)
    monkeypatch.setattr(ToolDiscovery, "_java_version", lambda path: version)

    jdk = ToolDiscovery.find_jdk(env=env, project=tmp_path)

    assert jdk.available
    assert jdk.version == "17.0"
    assert jdk.command == java
    assert "11" not in jdk.version
    assert "VERSION_11" not in jdk.message


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
