from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from ..llm import StructuredPipeline
from ..models import (
    EvaluationCriterion,
    EvaluationResult,
    Evidence,
    Exercise,
)
from ..tools.discovery import ToolDiscovery, ToolUnavailable
from ..tools.inspector import ProjectInspector
from ..tools.subprocess import SubprocessRunner
from ..urns import URN
from .base import ActionResult, ActionServices

DIMENSIONS = (
    "functional_requirements",
    "tests",
    "code_quality",
    "architecture",
    "android_practices",
)

TOP_LEVEL_WEIGHTS: dict[str, float] = {
    "functional_requirements": 0.40,
    "tests": 0.20,
    "code_quality": 0.15,
    "architecture": 0.15,
    "android_practices": 0.10,
}

SEVERITIES = ("error", "warning", "info")


class EvaluationAborted(Exception):
    pass


class InstrumentedNotSupportedError(Exception):
    pass


@dataclass
class EvaluateInput:
    exercise_id: str | None = None
    instrumented: bool = False
    confirmed: bool = False


class Rubric:
    """Deterministic 0-4 per-dimension scoring against the 40/20/15/15/10 rubric."""

    weights = TOP_LEVEL_WEIGHTS

    @classmethod
    def validate_weights(
        cls, functional_criteria: list[EvaluationCriterion] | None = None
    ) -> None:
        total = sum(cls.weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"top-level weights must sum to 1.0, got {total}")
        func = [
            c
            for c in (functional_criteria or [])
            if c.dimension == "functional_requirements"
        ]
        if func:
            sub = sum(c.weight for c in func)
            if abs(sub - 1.0) > 1e-6:
                raise ValueError(
                    f"functional subweights must sum to 1.0, got {sub}"
                )

    @staticmethod
    def _score_tests(evidence: list[Evidence]) -> int | None:
        ev = [e for e in evidence if e.type in {"unit_test", "test_report"}]
        if not ev:
            return None
        failures = sum(1 for e in ev if e.status in {"fail", "missing"})
        passes = sum(1 for e in ev if e.status == "pass")
        if failures:
            return 1
        if passes:
            return 4 if len(ev) == passes else 3
        return None

    @staticmethod
    def _score_static(evidence: list[Evidence]) -> int | None:
        if not evidence:
            return None
        if any(e.status == "missing" for e in evidence):
            return None
        errors = sum(1 for e in evidence if e.severity == "error")
        warnings = sum(1 for e in evidence if e.severity == "warning")
        infos = sum(1 for e in evidence if e.severity == "info")
        if errors:
            return 1
        if warnings:
            return 2 if warnings > 3 else 3
        if infos:
            return 3
        if any(e.status == "pass" for e in evidence):
            return 4
        return None

    @staticmethod
    def _score_architecture(evidence: list[Evidence]) -> int | None:
        ev = [e for e in evidence if e.type == "structure"]
        if not ev:
            return None
        missing = sum(1 for e in ev if e.status == "missing")
        passes = sum(1 for e in ev if e.status == "pass")
        if missing and passes:
            return 2
        if missing:
            return 1
        return 4 if passes >= 2 else 3

    @staticmethod
    def _score_structural_build(evidence: list[Evidence]) -> int | None:
        compile_ev = [e for e in evidence if e.type == "compilation"]
        if not compile_ev:
            return None
        if any(e.status == "missing" for e in compile_ev):
            return None
        if any(e.status == "fail" for e in compile_ev):
            return None
        return 3

    @classmethod
    def dimension_score(
        cls, dimension: str, evidence: list[Evidence]
    ) -> int | None:
        if dimension == "tests":
            return cls._score_tests(evidence)
        if dimension == "code_quality":
            return cls._score_static(
                [e for e in evidence if e.source == "detekt"]
            )
        if dimension == "android_practices":
            return cls._score_static([e for e in evidence if e.source == "lint"])
        if dimension == "architecture":
            return cls._score_architecture(evidence)
        if dimension == "functional_requirements":
            return cls._score_structural_build(evidence)
        return None

    @classmethod
    def functional_dimension_score(
        cls, criteria: list[EvaluationCriterion]
    ) -> tuple[float | None, list[EvaluationCriterion]]:
        evaluated = [
            c
            for c in criteria
            if c.dimension == "functional_requirements" and c.score is not None
        ]
        if not evaluated:
            return None, criteria
        total_weight = sum(c.weight for c in evaluated)
        if total_weight <= 0:
            return None, criteria
        score = sum(c.weight * c.score for c in evaluated) / total_weight
        return score, criteria

    @classmethod
    def compute(
        cls,
        dimension_scores: dict[str, int | None],
        functional_criteria: list[EvaluationCriterion] | None = None,
    ) -> tuple[float | None, dict[str, float | None]]:
        cls.validate_weights(functional_criteria)
        final: dict[str, float | None] = dict(dimension_scores)
        func_score, _ = cls.functional_dimension_score(functional_criteria or [])
        if func_score is not None:
            final["functional_requirements"] = func_score

        evaluated = [
            (d, s)
            for d, s in final.items()
            if s is not None and d in cls.weights
        ]
        if not evaluated:
            return None, final
        numerator = sum(cls.weights[d] * (s / 4.0) for d, s in evaluated)
        denominator = sum(cls.weights[d] for d, _ in evaluated)
        if denominator <= 0:
            return None, final
        overall = 100.0 * numerator / denominator
        return round(overall, 1), final

    @staticmethod
    def criterion_weight(
        requirement_id: str, criteria: list[EvaluationCriterion], fallback: float
    ) -> float:
        for c in criteria:
            if c.requirement_id == requirement_id:
                return c.weight
        return fallback

    @classmethod
    def requirement_score(cls, criterion: EvaluationCriterion) -> int | None:
        evidence = criterion.evidence
        if not evidence:
            return None
        if any(e.status == "fail" and e.type != "compilation" for e in evidence):
            return 0
        if any(e.type == "unit_test" and e.status == "pass" for e in evidence):
            return 4
        if any(e.status == "pass" and e.type == "structure" for e in evidence):
            return 3
        if any(e.status == "pass" and e.type == "compilation" for e in evidence):
            return 2
        if any(e.status == "missing" for e in evidence):
            return None
        return None


class AndroidProjectAnalyzer:
    def __init__(self, project_path: str | Path) -> None:
        self.project_path = Path(project_path).resolve()
        self.inspector = ProjectInspector(self.project_path)

    def analyze(self) -> list[Evidence]:
        evidence: list[Evidence] = []
        evidence.append(
            self._check("gradle wrapper present", "gradlew", "structure")
        )
        evidence.append(
            self._check(
                "Android manifest present",
                "app/src/main/AndroidManifest.xml",
                "structure",
            )
        )
        evidence.append(
            self._check(
                "debug variant manifest present",
                "app/src/debug/AndroidManifest.xml",
                "structure",
            )
        )
        evidence.append(
            self._check("Kotlin source directory", "app/src/main/java", "structure")
        )
        build_files = [
            p
            for p in self.inspector.structure()
            if p == "build.gradle.kts" or p.endswith("/build.gradle.kts")
        ]
        evidence.append(
            Evidence(
                source="file",
                type="structure",
                status="pass" if build_files else "missing",
                message="build file(s): " + ", ".join(build_files) or "none",
            )
        )
        return evidence

    def _check(self, message: str, relpath: str, type: str) -> Evidence:
        return Evidence(
            source="file",
            type=type,
            status="pass" if self.inspector.exists(relpath) else "missing",
            message=message,
            file=relpath,
        )


class GradleTool:
    def __init__(
        self,
        project_path: str,
        runner: SubprocessRunner | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.project_path = Path(project_path).resolve()
        self.runner = runner or SubprocessRunner()
        self._env = env

    def _wrapper(self) -> Path:
        gradle = ToolDiscovery.find_gradle(self.project_path, env=self._env)
        if not gradle.available:
            raise ToolUnavailable(gradle.message)
        return Path(gradle.command or "")

    def run_task(self, task: str, timeout: int | None = None) -> Evidence:
        try:
            wrapper = self._wrapper()
        except ToolUnavailable as exc:
            return Evidence(
                source="build",
                type="compilation",
                status="missing",
                message=f"limitation: {exc}",
            )
        result = self.runner.run(
            [str(wrapper), task],
            cwd=self.project_path,
            timeout=timeout,
        )
        return result.to_evidence("build", "compilation")

    def build(self, timeout: int | None = None) -> Evidence:
        return self.run_task("assembleDebug", timeout=timeout)


class TestTool:
    def __init__(
        self,
        project_path: str,
        runner: SubprocessRunner | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.project_path = Path(project_path).resolve()
        self.runner = runner or SubprocessRunner()
        self._env = env

    def _gradle(self) -> GradleTool:
        return GradleTool(str(self.project_path), runner=self.runner, env=self._env)

    def run_unit_tests(self, timeout: int | None = None) -> list[Evidence]:
        gradle_tool = self._gradle()
        try:
            result = gradle_tool.runner.run(
                [str(Path(gradle_tool._wrapper())), "testDebugUnitTest"],
                cwd=self.project_path,
                timeout=timeout,
            )
        except ToolUnavailable as exc:
            return [
                Evidence(
                    source="test",
                    type="unit_test",
                    status="missing",
                    message=f"limitation: {exc}",
                )
            ]
        command_evidence = result.to_evidence("test", "unit_test")
        report_evidence = self._parse_reports()
        if not report_evidence:
            return [command_evidence]
        return [command_evidence, *report_evidence]

    def _parse_reports(self) -> list[Evidence]:
        reports = self._report_files()
        if not reports:
            return []
        evidence: list[Evidence] = []
        for report in reports:
            try:
                root = ET.parse(str(report)).getroot()
            except ET.ParseError:
                continue
            for suite in root.iter("testsuite"):
                name = suite.get("name", report.stem)
                failures = int(suite.get("failures", "0"))
                errors = int(suite.get("errors", "0"))
                tests = int(suite.get("tests", "0"))
                status = "pass" if failures == 0 and errors == 0 else "fail"
                evidence.append(
                    Evidence(
                        source="test",
                        type="unit_test",
                        status=status,
                        message=f"{name}: {tests} tests, {failures} failures",
                        file=str(report),
                    )
                )
        return evidence

    def _report_files(self) -> list[Path]:
        patterns = (
            "app/build/test-results/**/*.xml",
            "build/test-results/**/*.xml",
        )
        found: list[Path] = []
        for pattern in patterns:
            found.extend(sorted(self.project_path.glob(pattern)))
        return found


class StaticAnalysisTool:
    def __init__(
        self,
        project_path: str,
        runner: SubprocessRunner | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.project_path = Path(project_path).resolve()
        self.runner = runner or SubprocessRunner()
        self._env = env

    def _gradle(self) -> GradleTool:
        return GradleTool(str(self.project_path), runner=self.runner, env=self._env)

    def run_all(self, timeout: int | None = None) -> list[Evidence]:
        evidence: list[Evidence] = []
        evidence.extend(self.run_lint(timeout=timeout))
        evidence.extend(self.run_detekt(timeout=timeout))
        return evidence

    def run_lint(self, timeout: int | None = None) -> list[Evidence]:
        gradle_tool = self._gradle()
        try:
            command = str(Path(gradle_tool._wrapper()))
        except ToolUnavailable as exc:
            return [
                Evidence(
                    source="lint",
                    type="android_lint",
                    status="missing",
                    severity=None,
                    message=f"limitation: {exc}",
                )
            ]
        result = gradle_tool.runner.run(
            [command, "lint"], cwd=self.project_path, timeout=timeout
        )
        findings = self._parse_lint_reports()
        if not findings:
            return [result.to_evidence("lint", "android_lint")]
        return [result.to_evidence("lint", "android_lint"), *findings]

    def run_detekt(self, timeout: int | None = None) -> list[Evidence]:
        gradle_tool = self._gradle()
        try:
            command = str(Path(gradle_tool._wrapper()))
        except ToolUnavailable as exc:
            return [
                Evidence(
                    source="detekt",
                    type="detekt",
                    status="missing",
                    severity=None,
                    message=f"limitation: {exc}",
                )
            ]
        result = gradle_tool.runner.run(
            [command, "detekt"], cwd=self.project_path, timeout=timeout
        )
        findings = self._parse_detekt_reports()
        if not findings:
            return [result.to_evidence("detekt", "detekt")]
        return [result.to_evidence("detekt", "detekt"), *findings]

    def _parse_lint_reports(self) -> list[Evidence]:
        reports = list(self.project_path.glob("app/build/reports/lint-results-*.xml"))
        findings: list[Evidence] = []
        for report in reports:
            try:
                root = ET.parse(str(report)).getroot()
            except ET.ParseError:
                continue
            for issue in root.iter("issue"):
                severity = (issue.get("severity") or "info").lower()
                if severity not in SEVERITIES:
                    severity = "info"
                location = issue.find("location")
                findings.append(
                    Evidence(
                        source="lint",
                        type="android_lint",
                        severity=severity,
                        status="fail" if severity == "error" else "pass",
                        message=issue.get("message", ""),
                        file=location.get("file") if location is not None else None,
                        line=location.get("line") if location is not None else None,
                        command="gradle lint",
                    )
                )
        return findings

    def _parse_detekt_reports(self) -> list[Evidence]:
        reports = list(self.project_path.glob("build/reports/detekt/*.xml")) + list(
            self.project_path.glob("app/build/reports/detekt/*.xml")
        )
        findings: list[Evidence] = []
        for report in reports:
            try:
                root = ET.parse(str(report)).getroot()
            except ET.ParseError:
                continue
            for file_node in root.iter("file"):
                filename = file_node.get("name")
                for error in file_node.iter("error"):
                    severity = (error.get("severity") or "info").lower()
                    if severity not in SEVERITIES:
                        severity = "info"
                    findings.append(
                        Evidence(
                            source="detekt",
                            type="detekt",
                            severity=severity,
                            status="fail" if severity == "error" else "pass",
                            message=error.get("message", ""),
                            file=filename,
                            line=error.get("line"),
                            command="gradle detekt",
                        )
                    )
        return findings


class RequirementMatcher:
    def __init__(
        self,
        exercise: Exercise | None,
        build_evidence: Evidence | None,
    ) -> None:
        self.exercise = exercise
        self.build_evidence = build_evidence

    def match(
        self, dimension_evidence: dict[str, list[Evidence]]
    ) -> list[EvaluationCriterion]:
        criteria: list[EvaluationCriterion] = []
        if self.exercise is None:
            return criteria

        req_ids = [r.id for r in self.exercise.requirements]
        weight = 1.0 / len(req_ids) if req_ids else 0.0
        for req in self.exercise.requirements:
            matching = self._evidence_for_requirement(
                req.id, req.summary, dimension_evidence
            )
            criterion = EvaluationCriterion(
                requirement_id=req.id,
                dimension="functional_requirements",
                weight=Rubric.criterion_weight(
                    req.id, self.exercise.evaluation_criteria, weight
                ),
                evidence=matching,
            )
            criterion.score = Rubric.requirement_score(criterion)
            criteria.append(criterion)
        return criteria

    def _evidence_for_requirement(
        self,
        requirement_id: str,
        summary: str,
        dimension_evidence: dict[str, list[Evidence]],
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        if self.build_evidence is not None and self.build_evidence.status == "pass":
            evidence.append(self.build_evidence)
        words = {w for w in summary.lower().split() if len(w) > 3}
        for e in dimension_evidence.get("structure", []):
            if e.file and any(w in e.file.lower() for w in words):
                evidence.append(e)
        for e in dimension_evidence.get("unit_test", []):
            if any(w in (e.message or "").lower() for w in words):
                evidence.append(e)
        if not words:
            evidence.extend(dimension_evidence.get("unit_test", []))
        return evidence


class EvaluationInterpretation(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    feedback: str = ""
    recommendations: list[str] = Field(default_factory=list)
    next_learning_activity: str = ""


class EvaluationAgent:
    SYSTEM = (
        "You are ADA Sensei's evaluation interpreter. You receive objective "
        "evidence and deterministic dimension scores. You interpret them "
        "pedagogically. You MUST NOT invent evidence and MUST NOT change the "
        "given scores. Supply strengths, weaknesses, feedback, "
        "recommendations, and a next learning activity as strictly valid JSON "
        "matching the EvaluationInterpretation schema."
    )

    def __init__(self, services: ActionServices) -> None:
        self.services = services

    def interpret(
        self,
        dimensions: dict[str, float | None],
        evidence: list[Evidence],
    ) -> EvaluationInterpretation:
        if self.services.client is None:
            return EvaluationInterpretation(
                feedback="LLM interpretation unavailable (no LLM client).",
                strengths=[],
                weaknesses=[],
                recommendations=[
                    "LLM interpretation could not run because no LLM client "
                    "is available."
                ],
                next_learning_activity="",
            )
        evidence_summary = "\n".join(
            f"- [{e.source}][{e.status}] {e.message[:200]}"
            for e in evidence[:40]
        ) or "(no evidence)"
        dimension_summary = ", ".join(
            f"{k}={v}" for k, v in sorted(dimensions.items()) if v is not None
        )
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self.SYSTEM,
            },
            {
                "role": "user",
                "content": (
                    "Deterministic dimension scores:\n"
                    f"{dimension_summary or '(none evaluated)'}\n\n"
                    "Evidence:\n"
                    f"{evidence_summary}\n\n"
                    "Interpret only; do not invent evidence and do not change scores."
                ),
            },
        ]
        pipeline = StructuredPipeline(
            self.services.client,
            max_attempts=self.services.config.llm.max_attempts,
            temperature=self.services.config.llm.temperature,
        )
        return pipeline.run(
            messages,
            EvaluationInterpretation,
            model=self.services.config.llm.model,
        )


@dataclass
class EvalResult(ActionResult):
    result: EvaluationResult

    def present(self) -> str:
        overall = (
            self.result.overall_score
            if self.result.overall_score is not None
            else "not evaluated"
        )
        parts = [f"Overall score: {overall}"]
        for criterion in self.result.criteria:
            label = criterion.requirement_id or criterion.dimension
            score = criterion.score if criterion.score is not None else "not evaluated"
            parts.append(f"- {label}: {score}")
        if self.result.strengths:
            strengths = "\n".join(f"- {s}" for s in self.result.strengths)
            parts.append(f"Strengths:\n{strengths}")
        if self.result.weaknesses:
            weaknesses = "\n".join(f"- {w}" for w in self.result.weaknesses)
            parts.append(f"Weaknesses:\n{weaknesses}")
        if self.result.feedback:
            parts.append(self.result.feedback)
        if self.result.recommendations:
            recs = "\n".join(f"- {r}" for r in self.result.recommendations)
            parts.append(f"Recommendations:\n{recs}")
        if self.result.next_learning_activity:
            parts.append(
                f"Next learning activity: {self.result.next_learning_activity}"
            )
        if self.result.limitations:
            limitations = "\n".join(
                f"- {lim}" for lim in self.result.limitations
            )
            parts.append(f"Limitations:\n{limitations}")
        return "\n\n".join(parts)


class EvaluateAction:
    def __init__(
        self, services: ActionServices, runner: SubprocessRunner | None = None
    ) -> None:
        self.services = services
        self._runner = runner

    def run(self, inp: EvaluateInput | None = None) -> EvalResult:
        inp = inp or EvaluateInput()
        if inp.instrumented:
            raise InstrumentedNotSupportedError(
                "--instrumented (connectedAndroidTest) is reserved for a future "
                "option and is not supported now"
            )

        project_path = self.services.config.project.path
        if project_path in (None, ""):
            raise LookupError("no active project configured")

        exercise = self._resolve_exercise(inp.exercise_id)
        build_failed = False
        limitations: list[str] = []

        if not inp.confirmed:
            raise EvaluationAborted(
                "confirmation required before executing Gradle tasks; "
                "use interactive confirmation or --yes"
            )

        runner = self._runner or SubprocessRunner(
            timeout_seconds=self.services.config.tools.timeout_seconds,
            offline=self.services.config.tools.offline,
        )

        dim_evidence: dict[str, list[Evidence]] = {
            d: [] for d in DIMENSIONS
        }

        analyzer = AndroidProjectAnalyzer(project_path)
        structure = analyzer.analyze()
        dim_evidence["architecture"].extend(structure)

        gradle = GradleTool(project_path, runner=runner)
        build_evidence = gradle.build()
        if build_evidence.status == "missing":
            limitations.append(
                "build could not execute (missing tooling/timeout): "
                f"{build_evidence.message}"
            )
        build_failed = build_evidence.status == "fail"
        dim_evidence["functional_requirements"].append(build_evidence)

        test_tool = TestTool(project_path, runner=runner)
        unit_evidence = test_tool.run_unit_tests()
        dim_evidence["tests"].extend(unit_evidence)

        static_tool = StaticAnalysisTool(project_path, runner=runner)
        static_evidence = static_tool.run_all()
        for ev in static_evidence:
            if ev.source == "lint":
                dim_evidence["android_practices"].append(ev)
            elif ev.source == "detekt":
                dim_evidence["code_quality"].append(ev)

        requirement_criteria: list[EvaluationCriterion] = []
        if build_failed:
            limitations.append(
                "build failed; requirement-level and compilation-dependent "
                "criteria are not evaluated. Fix the build first."
            )
        elif exercise is not None:
            matcher = RequirementMatcher(exercise, build_evidence)
            requirement_criteria = matcher.match(dim_evidence)

        dimension_scores: dict[str, int | None] = {
            d: Rubric.dimension_score(d, dim_evidence[d]) for d in DIMENSIONS
        }
        if exercise is None:
            dimension_scores["functional_requirements"] = None

        all_evidence = [
            e
            for ev_group in dim_evidence.values()
            for e in ev_group
        ]

        overall, final_dimensions = Rubric.compute(
            dimension_scores, requirement_criteria
        )

        try:
            interpretation = EvaluationAgent(self.services).interpret(
                final_dimensions, all_evidence
            )
        except Exception as exc:
            limitations.append(
                f"LLM interpretation failed (structured output or provider): {exc}"
            )
            interpretation = EvaluationInterpretation(
                feedback="LLM interpretation failed; deterministic scoring remains.",
                recommendations=[
                    "Retry the evaluation when the LLM provider is available."
                ],
            )

        student_id = self.services.context.student_id
        attempt_id = self.services.context.attempt_id or None
        result = EvaluationResult(
            id=URN.make("result"),
            attempt_id=attempt_id,
            exercise_id=exercise.id if exercise else None,
            student_id=student_id,
            project_id=URN.project_id_from_path(str(project_path)),
            overall_score=overall,
            criteria=[
                *requirement_criteria,
                *self._top_level_criteria(final_dimensions),
            ],
            strengths=interpretation.strengths,
            weaknesses=interpretation.weaknesses,
            feedback=interpretation.feedback,
            recommendations=interpretation.recommendations,
            next_learning_activity=interpretation.next_learning_activity,
            limitations=limitations,
        )

        self._persist(result, student_id, attempt_id, limitations)
        return EvalResult(result=result)

    @staticmethod
    def _top_level_criteria(
        final_dimensions: dict[str, float | None],
    ) -> list[EvaluationCriterion]:
        criteria: list[EvaluationCriterion] = []
        for dimension in DIMENSIONS:
            if dimension == "functional_requirements":
                continue
            score = final_dimensions.get(dimension)
            criteria.append(
                EvaluationCriterion(
                    requirement_id=None,
                    dimension=dimension,
                    weight=TOP_LEVEL_WEIGHTS.get(dimension, 1.0),
                    score=round(score) if score is not None else None,
                )
            )
        return criteria

    def _resolve_exercise(self, exercise_id: str | None) -> Exercise | None:
        uri = exercise_id or self.services.context.current_exercise_id
        if not uri:
            return None
        exercise = self.services.exercises.get(uri)
        if exercise is None:
            raise LookupError(f"unknown exercise: {uri}")
        return exercise

    def _persist(
        self,
        result: EvaluationResult,
        student_id: str | None,
        attempt_id: str | None,
        limitations: list[str],
    ) -> None:
        try:
            self.services.results.save(result)
        except Exception as exc:
            limitations.append(f"result {result.id} was NOT persisted: {exc}")
        if attempt_id:
            try:
                self.services.attempts.mark_completed(attempt_id)
            except Exception as exc:
                limitations.append(
                    f"attempt {attempt_id} was NOT marked completed: {exc}"
                )
        if student_id:
            try:
                self.services.history.append_evaluation(student_id, result)
            except Exception as exc:
                limitations.append(
                    f"evaluation outcome NOT appended to history for "
                    f"{student_id}: {exc}"
                )