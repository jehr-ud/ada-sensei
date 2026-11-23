"""Load and validate the pinned, auditable toolchain policy (RQ-EXM-066/075)."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import ToolId, ToolStatus

PINNED_RESOLUTION_POLICY = "pinned-compatible-only"
DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "007-examine"
    / "toolchain-policy.json"
)

_VERSION_ALIASES = {
    "java": "jdk",
    "java_version": "jdk",
    "jdk_version": "jdk",
    "gradle_version": "gradle",
    "gradle_wrapper": "gradle",
    "kotlin_version": "kotlin",
    "agp_version": "agp",
    "android_gradle_plugin": "agp",
}
_TOOL_ALIASES = {
    "android-lint": "android_lint",
    "androidlint": "android_lint",
    "kt-lint": "ktlint",
    "kt_lint": "ktlint",
}
_FLOATING_VERSION = re.compile(r"^(?:latest|latest\.release)$", re.IGNORECASE)
_DYNAMIC_VERSION = re.compile(r"\+$")
_ENTRY_FIELDS = {"jdk", "gradle", "kotlin", "agp", "tools", "checksums"}
_RUNTIME_FIELDS = ("jdk", "gradle", "kotlin", "agp")


class PolicyError(ValueError):
    """The policy is missing, malformed, or violates pinned-version guarantees."""


def _version_of(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("version") or value.get("value")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_version(value: Any) -> str | None:
    text = _version_of(value)
    if text is None:
        return None
    return text[1:] if text[:1].lower() == "v" and text[1:2].isdigit() else text


def _is_floating(value: Any) -> bool:
    text = _version_of(value)
    if text is None:
        return False
    return bool(_FLOATING_VERSION.match(text) or _DYNAMIC_VERSION.search(text))


def _reject_floating(value: Any, path: str = "policy") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floating(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_floating(item, f"{path}[{index}]")
    elif _is_floating(value):
        raise PolicyError(
            f"{path} uses floating version {value!r}; only pinned versions from "
            "compatibility_matrix are allowed"
        )


class CompatibilityEntry(BaseModel):
    jdk: str | None = None
    gradle: str | None = None
    kotlin: str | None = None
    agp: str | None = None
    tools: dict[str, str] = Field(default_factory=dict)
    checksums: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = dict(data)
        tools = dict(raw.pop("tools", {}) or {})
        for key, value in list(raw.items()):
            name = str(key).strip().lower().replace("-", "_")
            if name in _VERSION_ALIASES:
                raw[_VERSION_ALIASES[name]] = value
            elif name in {tool.value for tool in ToolId} or name in _TOOL_ALIASES:
                tools[_TOOL_ALIASES.get(name, name)] = value
        normalized = {
            key: value
            for key, value in raw.items()
            if str(key).strip().lower().replace("-", "_") in _ENTRY_FIELDS
        }
        normalized["tools"] = {
            str(key).strip().lower().replace("-", "_"): version
            for key, version in tools.items()
        }
        return normalized

    @field_validator("jdk", "gradle", "kotlin", "agp")
    @classmethod
    def _check_pinned(cls, value: str | None) -> str | None:
        if _is_floating(value):
            raise ValueError(f"floating runtime version {value!r} is not allowed")
        return value

    @field_validator("tools")
    @classmethod
    def _check_tool_versions(cls, value: dict[str, str]) -> dict[str, str]:
        for tool, version in value.items():
            if _is_floating(version):
                raise ValueError(f"floating version {version!r} for {tool}")
        return value

    def version_for(self, tool: ToolId) -> str | None:
        version = _version_of(self.tools.get(tool.value))
        if tool is ToolId.android_lint and version is None:
            return _version_of(self.agp)
        return version


class ToolPolicy(BaseModel):
    provider: str = ""
    required: bool = True
    version_source: str | None = None
    task_resolution: list[str] = Field(default_factory=list)
    report_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"provider": data}
        return data


class ToolchainPolicy(BaseModel):
    model_config = ConfigDict(extra="allow")

    policy_id: str = "ada-sensei-android-toolchain"
    policy_version: str = ""
    resolution_policy: str = PINNED_RESOLUTION_POLICY
    repositories: list[str] = Field(default_factory=list)
    compatibility_matrix: list[CompatibilityEntry] = Field(default_factory=list)
    tools: dict[ToolId, ToolPolicy] = Field(default_factory=dict)
    execution: dict[str, Any] = Field(default_factory=dict)
    network: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = dict(data)
        policy_tools = {}
        for key, value in (raw.get("tools") or {}).items():
            tool = str(key).strip().lower().replace("-", "_")
            tool = _TOOL_ALIASES.get(tool, tool)
            if tool in {item.value for item in ToolId}:
                policy_tools[tool] = value
        if "tools" in raw:
            raw["tools"] = policy_tools
        if not policy_tools:
            raw.pop("tools", None)
        return raw

    @model_validator(mode="after")
    def _validate_policy(self) -> ToolchainPolicy:
        if self.resolution_policy != PINNED_RESOLUTION_POLICY:
            raise PolicyError(
                f"unsupported resolution_policy {self.resolution_policy!r}; "
                f"expected {PINNED_RESOLUTION_POLICY!r}"
            )
        _reject_floating(self.model_dump())
        forbidden = (
            "allow_global_install",
            "allow_source_mutation",
            "allow_auto_correct",
        )
        for flag in forbidden:
            if self.execution.get(flag) is True:
                raise PolicyError(f"policy enables forbidden execution flag {flag}")
        if self.network.get("allow_unlisted_repositories") is True:
            raise PolicyError("policy allows unlisted repositories")
        if not self.tools:
            self.tools = {tool: ToolPolicy() for tool in ToolId}
        return self

    def required_tools(self) -> list[ToolId]:
        return [tool for tool in ToolId if self.tools.get(tool, ToolPolicy()).required]

    def resolve_versions(self, detected: Any) -> VersionResolution:
        required = self.required_tools()
        if not isinstance(detected, Mapping) and hasattr(detected, "detected_versions"):
            detected = detected.detected_versions()
        detected = {key: _clean_version(value) for key, value in detected.items()}
        statuses = {tool: ToolStatus.NOT_CONFIGURED for tool in required}
        versions = {tool: None for tool in required}
        blockers: list[str] = []

        if not self.compatibility_matrix:
            blocker = (
                "compatibility_matrix is empty: add a verified pinned combination "
                "(jdk, gradle, kotlin, agp, tools.detekt, tools.ktlint) to "
                "specs/007-examine/toolchain-policy.json before toolchain preflight"
            )
            return VersionResolution(
                statuses=statuses,
                versions=versions,
                blockers=[blocker],
            )

        entry = next(
            (item for item in self.compatibility_matrix if _matches(item, detected)),
            None,
        )
        if entry is None:
            observed = ", ".join(
                f"{key}={detected.get(key) or 'undetected'}" for key in _RUNTIME_FIELDS
            )
            supported = "; ".join(
                ", ".join(
                    f"{key}={getattr(item, key) or 'any'}" for key in _RUNTIME_FIELDS
                )
                for item in self.compatibility_matrix
            )
            blockers.append(
                "no pinned compatibility entry matches detected versions "
                f"({observed}); supported: {supported}. Align the project "
                "with a supported combination or add a verified entry to "
                "the policy"
            )
            return VersionResolution(
                statuses={tool: ToolStatus.INCOMPATIBLE for tool in required},
                versions=versions,
                blockers=blockers,
                entry=None,
            )

        for tool in required:
            version = entry.version_for(tool)
            if version is None:
                blockers.append(
                    f"{tool.value}: the matched compatibility entry does not pin a "
                    "version; add one to compatibility_matrix.tools"
                )
                continue
            versions[tool] = version
            statuses[tool] = ToolStatus.INSTALLED
        return VersionResolution(
            statuses=statuses,
            versions=versions,
            blockers=blockers,
            entry=entry,
        )


class VersionResolution(BaseModel):
    statuses: dict[ToolId, ToolStatus] = Field(default_factory=dict)
    versions: dict[ToolId, str | None] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    entry: CompatibilityEntry | None = None


def _matches(entry: CompatibilityEntry, detected: Mapping[str, str | None]) -> bool:
    for key in _RUNTIME_FIELDS:
        expected = _clean_version(getattr(entry, key))
        actual = detected.get(key)
        if expected and actual and expected != actual:
            return False
    return True


def load_policy(path: str | Path | None = None) -> ToolchainPolicy:
    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PolicyError(f"cannot read toolchain policy {policy_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyError(
            f"invalid JSON in toolchain policy {policy_path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PolicyError(f"toolchain policy {policy_path} must be a JSON object")
    try:
        return ToolchainPolicy.model_validate(payload)
    except (PolicyError, ValueError) as exc:
        raise PolicyError(f"invalid toolchain policy {policy_path}: {exc}") from exc


def resolve_versions(policy: ToolchainPolicy, detected: Any) -> VersionResolution:
    return policy.resolve_versions(detected)


__all__ = [
    "CompatibilityEntry",
    "DEFAULT_POLICY_PATH",
    "PINNED_RESOLUTION_POLICY",
    "PolicyError",
    "ToolPolicy",
    "ToolchainPolicy",
    "VersionResolution",
    "load_policy",
    "resolve_versions",
]
