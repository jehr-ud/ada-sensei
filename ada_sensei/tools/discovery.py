from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

JDK_MINIMUM = (17, 0)
_GRADLE_DAEMON_JVM_FILE = Path("gradle") / "gradle-daemon-jvm.properties"
_TOOLCHAIN_VERSION = re.compile(
    r"^\s*toolchainVersion\s*=\s*(\d+(?:\.\d+)?)\s*$", re.MULTILINE
)


def _version_tuple(value: str) -> tuple[int, int] | None:
    parts = value.split(".")
    if len(parts) > 2 or not all(part.isdigit() for part in parts):
        return None
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) == 2 else 0
    return (major, minor)


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
    def find_gradle_jvm(project: str | Path | None) -> Tool:
        """Detect the JVM version declared for the Gradle daemon.

        The declaration is metadata about the JVM Gradle intends to use; it is
        never an installed JDK. Resolution precedence in :meth:`find_jdk` is
        ``JAVA_HOME``, then ``java`` on ``PATH``, then this declaration as
        explanatory metadata. Compile targets such as ``sourceCompatibility``
        are not runtime JVM sources and are never read here.
        """
        if not project:
            return Tool(
                name="gradle-jvm",
                command=None,
                message="Gradle daemon JVM version not declared",
            )
        properties = Path(project) / _GRADLE_DAEMON_JVM_FILE
        if not properties.is_file():
            return Tool(
                name="gradle-jvm",
                command=None,
                message="Gradle daemon JVM version not declared",
            )
        try:
            text = properties.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return Tool(
                name="gradle-jvm",
                command=str(properties),
                message="Gradle daemon JVM version could not be read",
            )
        match = _TOOLCHAIN_VERSION.search(text)
        if match is None:
            return Tool(
                name="gradle-jvm",
                command=str(properties),
                message="Gradle daemon JVM version is missing or invalid",
            )
        version = match.group(1)
        parsed = _version_tuple(version)
        if parsed is None:
            return Tool(
                name="gradle-jvm",
                command=str(properties),
                message="Gradle daemon JVM version is missing or invalid",
            )
        return Tool(
            name="gradle-jvm",
            command=str(properties),
            version=version,
            available=parsed >= JDK_MINIMUM,
        )

    @staticmethod
    def find_jdk(
        env: dict[str, str] | None = None, project: str | Path | None = None
    ) -> Tool:
        """Find an installed JDK, then report a declared Gradle JVM if present.

        Precedence: ``JAVA_HOME``, ``java`` on ``PATH``, then
        ``gradle/gradle-daemon-jvm.properties:toolchainVersion``. Installed
        executables decide ``available`` and the reported runtime ``version``;
        a project declaration only adds context and never invents an installed
        JDK. ``sourceCompatibility``/``targetCompatibility`` are compile targets
        and are deliberately excluded.
        """
        env = env if env is not None else os.environ
        declared = ToolDiscovery.find_gradle_jvm(project)
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
                message = ""
                if declared.version:
                    message = (
                        f"Gradle daemon JVM {declared.version} declared in "
                        f"{declared.command}; using installed JDK"
                    )
                return Tool(
                    name="jdk",
                    command=candidate,
                    version=".".join(map(str, version)),
                    available=True,
                    message=message,
                )
            if version is not None:
                message = f"JDK {JDK_MINIMUM[0]}+ required, found {version[0]}"
                if declared.version:
                    message += (
                        f"; Gradle daemon JVM {declared.version} declared in "
                        f"{declared.command}"
                    )
                return Tool(
                    name="jdk",
                    command=candidate,
                    version=".".join(map(str, version)),
                    available=False,
                    message=message,
                )
        if declared.version:
            return Tool(
                name="jdk",
                command=declared.command,
                version=declared.version,
                available=False,
                message=(
                    f"Gradle daemon JVM {declared.version} is declared in "
                    f"{declared.command} but no installed JDK "
                    f"{JDK_MINIMUM[0]}+ was found (JAVA_HOME or PATH)"
                ),
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
        if project:
            local_props = Path(project) / "local.properties"
            if local_props.is_file():
                for line in local_props.read_text().splitlines():
                    if line.startswith("sdk.dir="):
                        candidate = line.split("=", 1)[1].strip()
                        if candidate:
                            return Tool(
                                name="android-sdk", command=candidate, available=True
                            )
        candidate = env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT")
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
            "jdk": ToolDiscovery.find_jdk(env=env, project=project),
            "android-sdk": ToolDiscovery.find_sdk(env=env, project=project),
        }
