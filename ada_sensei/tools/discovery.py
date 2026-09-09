from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

JDK_MINIMUM = (17, 0)


@dataclass
class Tool:
    name: str
    command: str | None
    version: str | None = None
    available: bool = False
    message: str = ""


class ToolUnavailable(Exception):
    pass


class ToolDiscovery:
    @staticmethod
    def find_gradle(
        project: str | Path | None = None, env: dict[str, str] | None = None
    ) -> Tool:
        env = env if env is not None else os.environ
        if project:
            wrapper = Path(project) / "gradlew"
            if wrapper.is_file():
                return Tool(
                    name="gradle",
                    command=str(wrapper),
                    version="wrapper",
                    available=True,
                )
        command = shutil.which("gradle", path=env.get("PATH"))
        if command:
            return Tool(name="gradle", command=command, available=True)
        return Tool(
            name="gradle",
            command=None,
            available=False,
            message="gradle wrapper or gradle not found",
        )

    @staticmethod
    def find_jdk(env: dict[str, str] | None = None) -> Tool:
        env = env if env is not None else os.environ
        candidates: list[str] = []
        java_home = env.get("JAVA_HOME")
        if java_home:
            candidates.append(str(Path(java_home) / "bin" / "java"))
        on_path = shutil.which("java", path=env.get("PATH"))
        if on_path:
            candidates.append(on_path)

        for candidate in candidates:
            version = ToolDiscovery._java_version(candidate)
            if version is not None and version >= JDK_MINIMUM:
                return Tool(
                    name="jdk",
                    command=candidate,
                    version=".".join(map(str, version)),
                    available=True,
                )
            if version is not None:
                return Tool(
                    name="jdk",
                    command=candidate,
                    version=".".join(map(str, version)),
                    available=False,
                    message=f"JDK {JDK_MINIMUM[0]}+ required, found {version[0]}",
                )
        return Tool(
            name="jdk",
            command=None,
            available=False,
            message="no JDK 17+ found (JAVA_HOME or PATH)",
        )

    @staticmethod
    def _java_version(java_path: str) -> tuple[int, int] | None:
        try:
            output = subprocess.run(
                [java_path, "-version"], capture_output=True, text=True, timeout=5
            ).stderr
        except (OSError, subprocess.TimeoutExpired):
            return None
        match = re.search(r'version "([0-9]+)(?:\.([0-9]+))?', output)
        if not match:
            return None
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        return (major, minor)

    @staticmethod
    def find_sdk(
        env: dict[str, str] | None = None, project: str | Path | None = None
    ) -> Tool:
        env = env if env is not None else os.environ
        candidate = env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT")
        if not candidate and project:
            local_props = Path(project) / "local.properties"
            if local_props.is_file():
                for line in local_props.read_text().splitlines():
                    if line.startswith("sdk.dir="):
                        candidate = line.split("=", 1)[1].replace("\\", "").strip()
                        break
        if candidate and Path(candidate).is_dir():
            return Tool(name="android-sdk", command=candidate, available=True)
        return Tool(
            name="android-sdk",
            command=None,
            available=False,
            message="Android SDK not found",
        )

    @staticmethod
    def discover(
        project: str | Path | None = None, env: dict[str, str] | None = None
    ) -> dict[str, Tool]:
        return {
            "gradle": ToolDiscovery.find_gradle(project, env=env),
            "jdk": ToolDiscovery.find_jdk(env=env),
            "android-sdk": ToolDiscovery.find_sdk(env=env, project=project),
        }
