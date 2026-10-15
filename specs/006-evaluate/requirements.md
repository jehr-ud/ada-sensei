# Requirements

## Evidence and Evaluation Engine

### RQ-EVA-001 Active project
The system SHALL identify the active Android project.

### RQ-EVA-002 Project inspection
The system SHALL inspect project structure and relevant source files.

### RQ-EVA-003 Gradle build
The system SHALL attempt the configured Gradle build.

### RQ-EVA-004 Test evidence
The system SHALL collect unit-test execution results when tests are available.

### RQ-EVA-005 Evidence association
The system SHALL associate evaluation criteria with collected evidence.

### RQ-EVA-006 Requirement evaluation
The system SHALL evaluate exercise requirements individually when requirement
definitions are available.

### RQ-EVA-007 Evidence versus interpretation
The system SHALL distinguish deterministic evidence from LLM interpretation.
The LLM SHALL NOT invent evidence, and the final score SHALL be recomputed
deterministically.

### RQ-EVA-008 Structured result
The evaluation result SHALL contain a structured score, evidence, limitations,
strengths, weaknesses, and feedback where available.

### RQ-EVA-009 Strengths
The system SHALL identify strengths as well as weaknesses.

### RQ-EVA-010 Next activity
The system SHOULD recommend a next learning activity based on detected weaknesses.

### RQ-EVA-011 Read-only source
Standard evaluation SHALL NOT modify student source files or project-owned code.

### RQ-EVA-012 Missing evidence
If build, tests, or analysis cannot execute, the system SHALL report the limitation
instead of treating missing evidence as success.

## Rubric

### RQ-EVA-013 Rubric scoring
The system SHALL support integer criterion scores from 0–4 and compute a normalized
0–100 score.

### RQ-EVA-014 Evidence sufficiency
A criterion without supporting evidence SHALL be `not_evaluated` and SHALL NOT be
assumed to pass or fail.

### RQ-EVA-015 Static analysis
The system SHALL collect Android Lint and Detekt findings through the project's
Gradle wrapper, preserving severity as `ERROR`, `WARNING`, or `INFO`.

Findings SHALL be evidence and SHALL NOT map one-to-one to grade deductions.

### RQ-EVA-016 Result persistence
The system SHALL persist and retrieve evaluation results through a stable
`result://<uuid>` identifier.

### RQ-EVA-017 Exercise resolution
The system SHALL resolve the exercise from explicit `--exercise`, then session
context, and otherwise perform structural-only evaluation.

### RQ-EVA-018 Build-failure policy
When the build fails, requirement-level and compilation-dependent criteria SHALL
be marked `not_evaluated` and the build failure SHALL be reported as a blocking
limitation.

### RQ-EVA-019 Gradle confirmation
The system SHALL require explicit confirmation before executing Gradle-based tasks.

### RQ-EVA-020 Default evidence scope
The default evaluation SHALL include project inspection, build, unit tests,
Android Lint, and Detekt.

### RQ-EVA-021 No instrumented tests
The system SHALL NOT run `connectedAndroidTest` by default.

### RQ-EVA-022 Evaluate rubric weights
The default `/evaluate` rubric SHALL use:
- functional requirements: 40%;
- tests: 20%;
- code quality: 15%;
- architecture: 15%;
- Android practices: 10%.

Where objective evidence exists, scoring SHALL be deterministic.

### RQ-EVA-023 Non-interactive confirmation
In a non-interactive environment, Gradle-based execution SHALL require explicit
`--yes`.

### RQ-EVA-024 Rubric hierarchy
The five default top-level dimensions SHALL sum to exactly 100%.

Exercise requirement subweights SHALL sum to 100% of the fixed functional
requirements dimension and SHALL NOT create additional top-level weight.

### RQ-EVA-025 Attempt completion
A successfully evaluated known attempt SHALL be marked `completed`.

### RQ-EVA-026 Evaluation history
A successful evaluation SHALL append its outcome to student history while
preserving `student_id`, `project_id`, `exercise_id`, and `attempt_id`.

### RQ-EVA-027 Persistence failure visibility
Persistence, attempt-completion, and history failures SHALL be reported explicitly.

## Reusable Evaluation Infrastructure

### RQ-EVA-028 Evaluation engine
The system SHALL expose a reusable evaluation-engine boundary that coordinates
project analysis, deterministic evidence collection, requirement matching,
rubric mechanics, and structured interpretation.

The engine SHALL be reusable without requiring callers to invoke `EvaluateAction`
directly.

### RQ-EVA-029 Reusable evidence context
Collected evidence SHALL be represented independently from `/evaluate` so another
workflow can consume the same evidence without duplicating Android analysis or
tool execution.

### RQ-EVA-030 Rubric abstraction
Rubric mechanics SHALL be separated from rubric definitions.

A rubric definition SHALL identify its version, dimensions, weights, score scale,
and optional subcriteria.

### RQ-EVA-031 Evaluate rubric isolation
The default `/evaluate` rubric SHALL be versioned and isolated from rubrics used
by other workflows.

A different workflow SHALL NOT modify the `/evaluate` weights implicitly.

### RQ-EVA-032 Reusable deterministic scoring
The rubric engine SHALL accept a validated rubric definition and compute scores
deterministically from supplied criterion/dimension scores and evidence status.

### RQ-EVA-033 Reusable requirement matching
Requirement matching SHALL be callable independently from the `/evaluate` action
and SHALL produce traceable evidence-to-requirement associations.

### RQ-EVA-034 Structured-output validation
Every structured LLM result used by the evaluation engine SHALL be schema validated.
Invalid output SHALL be retried up to a maximum of 3 total attempts. If all
attempts fail validation, the operation SHALL fail explicitly.

### RQ-EVA-035 No evidence invention
The evaluation engine SHALL reject or flag LLM claims that cannot be grounded in
available evidence. The final result SHALL identify unsupported claims rather than
silently treating them as evidence.

### RQ-EVA-036 Workflow reuse
Higher-level workflows, including `007-examine`, SHALL be able to reuse the
evaluation engine, evidence context, requirement matcher, and rubric mechanics
without modifying the default `/evaluate` behavior.

---

## Traceability

| Requirement | Primary component | Test |
|---|---|---|
| RQ-EVA-001 | AndroidProjectAnalyzer | `tests/actions/evaluate/test_analyzer.py::test_active_project` |
| RQ-EVA-002 | AndroidProjectAnalyzer | `tests/actions/evaluate/test_analyzer.py::test_structure_inspected` |
| RQ-EVA-003 | GradleTool | `tests/actions/evaluate/test_gradle.py::test_build_attempted` |
| RQ-EVA-004 | TestTool | `tests/actions/evaluate/test_tests.py::test_reports_collected` |
| RQ-EVA-005 | RequirementMatcher | `tests/actions/evaluate/test_requirements.py::test_evidence_linked` |
| RQ-EVA-006 | RequirementMatcher | `tests/actions/evaluate/test_requirements.py::test_individual_requirements` |
| RQ-EVA-007 | RubricEngine | `tests/actions/evaluate/test_rubric.py::test_score_recomputed_not_taken_from_input` |
| RQ-EVA-008 | EvaluationResult | `tests/actions/evaluate/test_result.py::test_structured_result` |
| RQ-EVA-009 | EvaluationAgent | `tests/actions/evaluate/test_eval.py::test_strengths_and_weaknesses` |
| RQ-EVA-010 | EvaluationAgent | `tests/actions/evaluate/test_eval.py::test_next_activity` |
| RQ-EVA-011 | EvaluateAction | `tests/actions/evaluate/test_eval.py::test_no_source_modification` |
| RQ-EVA-012 | EvaluateAction / GradleTool | `tests/actions/evaluate/test_gradle.py::test_limitation_not_success` |
| RQ-EVA-013 | RubricEngine | `tests/actions/evaluate/test_rubric.py::test_weighted_score` |
| RQ-EVA-014 | RequirementMatcher / RubricEngine | `tests/actions/evaluate/test_rubric.py::test_not_evaluated_excluded` |
| RQ-EVA-015 | StaticAnalysisTool | `tests/actions/evaluate/test_static.py::test_lint_detekt_report` |
| RQ-EVA-016 | ResultStore | `tests/actions/evaluate/test_eval.py::test_result_persisted` |
| RQ-EVA-017 | EvaluateAction | `tests/actions/evaluate/test_eval.py::test_exercise_resolution` |
| RQ-EVA-018 | EvaluateAction | `tests/actions/evaluate/test_eval.py::test_build_failure_blocking` |
| RQ-EVA-019 | CLI → EvaluateAction | `tests/actions/evaluate/test_eval.py::test_confirmation_required` |
| RQ-EVA-020 | EvaluationEngine | `tests/actions/evaluate/test_eval.py::test_default_scope` |
| RQ-EVA-021 | EvaluateAction | `tests/actions/evaluate/test_eval.py::test_instrumented_not_run` |
| RQ-EVA-022 | EVALUATE_RUBRIC | `tests/actions/evaluate/test_rubric.py::test_rubric_weights` |
| RQ-EVA-023 | CLI → EvaluateAction | `tests/actions/evaluate/test_eval.py::test_non_interactive_aborts_without_yes` |
| RQ-EVA-024 | RubricEngine | `tests/actions/evaluate/test_rubric.py::test_subweights_inside_functional_dimension` |
| RQ-EVA-025 | AttemptStore | `tests/storage/test_attempts.py::test_mark_completed_after_eval` |
| RQ-EVA-026 | HistoryStore | `tests/storage/test_history.py::test_append_evaluation_outcome` |
| RQ-EVA-027 | EvaluateAction | `tests/actions/evaluate/test_eval.py::test_persistence_failure_reported` |
| RQ-EVA-028 | EvaluationEngine | `tests/actions/evaluate/test_engine.py::test_engine_reusable` |
| RQ-EVA-029 | EvidenceContext | `tests/actions/evaluate/test_engine.py::test_evidence_context_is_independent` |
| RQ-EVA-030 | RubricDefinition / RubricEngine | `tests/actions/evaluate/test_rubric.py::test_rubric_definition_versioning` |
| RQ-EVA-031 | EVALUATE_RUBRIC | `tests/actions/evaluate/test_rubric.py::test_evaluate_rubric_isolated` |
| RQ-EVA-032 | RubricEngine | `tests/actions/evaluate/test_rubric.py::test_deterministic_reuse` |
| RQ-EVA-033 | RequirementMatcher | `tests/actions/evaluate/test_requirements.py::test_matcher_reusable` |
| RQ-EVA-034 | EvaluationAgent / structured parser | `tests/actions/evaluate/test_structured_output.py::test_three_attempt_limit` |
| RQ-EVA-035 | Evidence validator | `tests/actions/evaluate/test_structured_output.py::test_unsupported_claim_rejected` |
| RQ-EVA-036 | EvaluationEngine | `tests/actions/evaluate/test_engine.py::test_external_workflow_reuse` |
