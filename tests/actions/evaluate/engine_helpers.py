"""Shared fakes for the reusable-engine tests (ADR-022, RQ-EVA-028/036)."""

from __future__ import annotations

import json

from ada_sensei.evaluation import (
    EvaluationExecutionPolicy,
    EvidenceContext,
    ProjectContext,
    assign_evidence_ids,
)
from ada_sensei.llm.base import LLMClient
from ada_sensei.models import Evidence, Exercise, Requirement
from ada_sensei.tools.subprocess import SubprocessResult


class ScriptedClient(LLMClient):
    """Returns queued payloads; the last one repeats when the queue runs out."""

    def __init__(self, payloads: list[str] | None = None):
        self.payloads = list(payloads or [])
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, *, model=None, temperature=None):
        self.calls.append(list(messages))
        return self.payloads[0] if self.payloads else "{}"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        self.calls.append(list(messages))
        if not self.payloads:
            return "{}"
        return self.payloads.pop(0) if len(self.payloads) > 1 else self.payloads[0]


def interpretation_payload(
    *,
    strengths: list[tuple[str, list[str]]] | None = None,
    weaknesses: list[tuple[str, list[str]]] | None = None,
    recommendations: list[tuple[str, list[str]]] | None = None,
    findings: list[tuple[str, list[str]]] | None = None,
    feedback: str = "Grounded interpretation.",
    next_learning_activity: str = "Practice the weakest dimension.",
    limitations: list[str] | None = None,
) -> str:
    def claims(items):
        return [
            {"claim": text, "evidence_refs": refs, "kind": "finding"}
            for text, refs in (items or [])
        ]

    return json.dumps(
        {
            "strengths": claims(strengths),
            "weaknesses": claims(weaknesses),
            "recommendations": claims(recommendations),
            "findings": claims(findings),
            "feedback": feedback,
            "next_learning_activity": next_learning_activity,
            "limitations": limitations or [],
        }
    )


class StubRunner:
    """Subprocess stub with per-task exit codes."""

    def __init__(self, exit_codes: dict[str, int] | None = None, default: int = 0):
        self.exit_codes = exit_codes or {}
        self.default = default
        self.calls: list[list[str]] = []

    def run(self, cmd, *, cwd=None, timeout=None):
        self.calls.append(list(cmd))
        task = cmd[-1]
        return SubprocessResult(
            command=cmd,
            cwd=str(cwd),
            exit_code=self.exit_codes.get(task, self.default),
            stdout=f"{task} output",
            stderr="",
            duration_s=0.1,
        )


def make_project(path) -> ProjectContext:
    return ProjectContext.from_path(path)


def confirmed_policy(**overrides) -> EvaluationExecutionPolicy:
    policy = EvaluationExecutionPolicy(gradle_confirmed=True)
    return policy.model_copy(update=overrides) if overrides else policy


def make_exercise(
    requirement_ids=("req://r1",), summaries=("implement the task repository",)
) -> Exercise:
    return Exercise(
        id="exercise://e1",
        title="Task repository",
        requirements=[
            Requirement(id=rid, summary=summary)
            for rid, summary in zip(requirement_ids, summaries, strict=True)
        ],
        evaluation_criteria=[],
    )


def make_context(evidence: list[Evidence], **overrides) -> EvidenceContext:
    context = EvidenceContext(
        project_id="project://p1",
        project_path="/tmp/project",
        evidence=assign_evidence_ids(evidence),
    )
    return context.model_copy(update=overrides) if overrides else context


def compilation(status: str = "pass") -> Evidence:
    return Evidence(
        source="build", type="compilation", status=status, message="assembleDebug"
    )


def unit_test(status: str = "pass", message: str = "RepoTest: 3 tests, 0 failures"):
    return Evidence(source="test", type="unit_test", status=status, message=message)


def structure(status: str = "pass", file: str = "app/src/main/java/Repo.kt"):
    return Evidence(source="file", type="structure", status=status, file=file)


def lint(severity: str = "info", status: str = "pass") -> Evidence:
    return Evidence(
        source="lint",
        type="android_lint",
        severity=severity,
        status=status,
        message="lint finding",
    )


def detekt(severity: str = "warning", status: str = "pass") -> Evidence:
    return Evidence(
        source="detekt",
        type="detekt",
        severity=severity,
        status=status,
        message="detekt finding",
    )


def full_evidence() -> list[Evidence]:
    """The default scope with every tool available and clean."""
    return [
        structure(),
        structure(file="app/src/main/java/Other.kt"),
        compilation(),
        unit_test(),
        lint(),
        detekt(),
    ]
