# Requirements

## RQ-EVA-001

The system SHALL identify the active Android project.

## RQ-EVA-002

The system SHALL be able to inspect project structure and relevant source files.

## RQ-EVA-003

The system SHALL attempt to execute the project's Gradle build when configured to do so.

## RQ-EVA-004

The system SHALL collect test execution results when tests are available.

## RQ-EVA-005

The system SHALL associate evaluation criteria with evidence.

## RQ-EVA-006

The system SHALL evaluate exercise requirements individually when requirement definitions are available.

## RQ-EVA-007

The system SHALL distinguish objective evidence from LLM interpretation; overall scoring SHALL be recomputed deterministically from criterion evidence.

## RQ-EVA-008

The evaluation result SHALL contain a structured score and feedback.

## RQ-EVA-009

The system SHALL identify strengths as well as weaknesses.

## RQ-EVA-010

The system SHOULD recommend a next learning activity based on detected weaknesses.

## RQ-EVA-011

The system SHALL not modify the student's project during a standard evaluation.

## RQ-EVA-012

If build or tests cannot be executed, the system SHALL report the limitation instead of treating missing evidence as success.

## RQ-EVA-013 Rubric

The system SHALL evaluate each criterion on a 0–4 integer scale and compute an
overall 0–100 weighted score; criteria without evidence SHALL be excluded from
the score and reported as not evaluated (ADR-011).

## RQ-EVA-014 Evidence sufficiency

A criterion without supporting evidence SHALL be marked "not evaluated" and SHALL
never be assumed to pass or fail.

## RQ-EVA-015 Static analysis

The system SHALL run Android Lint and detekt through the project's Gradle wrapper
and collect their reports as evidence, preserving each finding's severity
(ERROR | WARNING | INFO). Findings SHALL be treated as evidence and SHALL NOT
automatically map one-to-one to grade deductions (ADR-012).

## RQ-EVA-016 Result persistence

The evaluation result SHALL be persisted and retrievable by its stable
`result://<uuid>` id (RQ-FND-013).

## RQ-EVA-017 Exercise resolution

The system SHALL resolve the exercise from `--exercise`, else the session
current exercise; with no exercise, only structural (non-requirement) dimensions
SHALL be evaluated and requirement scoring SHALL be skipped.

## RQ-EVA-018 Build-failure policy

When the build fails, requirement-level and compilation-dependent criteria SHALL
be marked not evaluated and the result SHALL list the build failure as the
blocking limitation with guidance to fix it first.

## RQ-EVA-019 Confirmation before Gradle execution

The system SHALL require explicit user confirmation before executing Gradle-based
tasks; declining SHALL abort the evaluation cleanly (ADR-016, RQ-CLI-014).

## RQ-EVA-020 Default evidence scope

The default evaluation SHALL run project inspection, the Gradle build,
unit tests, Android Lint, and detekt (ADR-016).

## RQ-EVA-021 No instrumented tests by default

The system SHALL NOT run `connectedAndroidTest` by default; instrumented-test
execution is reserved for a future explicit `--instrumented` option and SHALL be
rejected as unsupported today (ADR-016, RQ-CLI-015).

## RQ-EVA-022 Rubric weights

The rubric SHALL weight dimensions as: functional requirements 40%, tests 20%,
code quality 15%, architecture 15%, Android practices 10%. Where objective
evidence exists the score SHALL be deterministic; the LLM interprets evidence
but SHALL NOT invent it (ADR-017).


## RQ-EVA-023 Non-interactive confirmation

When `evaluate` is invoked in a non-interactive environment, Gradle-based
execution SHALL be blocked unless the explicit CLI confirmation override
`--yes` is supplied.

## RQ-EVA-024 Rubric hierarchy

The five top-level rubric dimensions SHALL be the complete scoring dimensions
and SHALL sum to exactly 100%: functional requirements 40%, tests 20%, code
quality 15%, architecture 15%, Android practices 10%.

When an exercise defines per-requirement `evaluation_criteria`, those criteria
are subcriteria of the fixed 40% functional-requirements dimension. Their
normalized subweights SHALL sum to exactly 100% of that dimension and SHALL NOT
create additional top-level score weight.

## RQ-EVA-025 Attempt completion

When an evaluation successfully completes for a known `attempt_id`, the system
SHALL mark that attempt as `completed`.

## RQ-EVA-026 Evaluation history

After successful evaluation, the evaluation outcome SHALL be appended to the
student history through `HistoryStore`, preserving `student_id`, `project_id`,
`exercise_id`, and `attempt_id`.

## RQ-EVA-027 Persistence failure visibility

If result persistence, attempt completion, or history update fails, the system
SHALL report the persistence failure explicitly and SHALL NOT claim that the
affected record was successfully stored.

---

## Traceability

| Requirement | Component | Test |
|---|---|---|
| RQ-EVA-001 | `AndroidProjectAnalyzer` | `tests/actions/evaluate/test_analyzer.py::test_active_project` |
| RQ-EVA-002 | `AndroidProjectAnalyzer` | `tests/actions/evaluate/test_analyzer.py::test_structure_inspected` |
| RQ-EVA-003 | `GradleTool` | `tests/actions/evaluate/test_gradle.py::test_build_attempted` |
| RQ-EVA-004 | `TestTool` | `tests/actions/evaluate/test_tests.py::test_reports_collected` |
| RQ-EVA-005 | `RequirementMatcher` | `tests/actions/evaluate/test_requirements.py::test_evidence_linked` |
| RQ-EVA-006 | `RequirementMatcher` | `tests/actions/evaluate/test_requirements.py::test_individual_requirements` |
| RQ-EVA-007 | `Rubric` | `tests/actions/evaluate/test_rubric.py::test_score_recomputed` |
| RQ-EVA-008 | `EvaluationResult` | `tests/actions/evaluate/test_rubric.py::test_structured_result` |
| RQ-EVA-009 | `EvaluationAgent` | `tests/actions/evaluate/test_eval.py::test_strengths_and_weaknesses` |
| RQ-EVA-010 | `EvaluationAgent` + `HistoryStore` | `tests/actions/evaluate/test_eval.py::test_next_activity` |
| RQ-EVA-011 | `EvaluateAction` | `tests/actions/evaluate/test_eval.py::test_no_source_modification` |
| RQ-EVA-012 | `EvaluateAction` / `GradleTool` | `tests/actions/evaluate/test_gradle.py::test_limitation_not_success` |
| RQ-EVA-013 | `Rubric` | `tests/actions/evaluate/test_rubric.py::test_weighted_score` / `test_not_evaluated_excluded` |
| RQ-EVA-014 | `RequirementMatcher` | `tests/actions/evaluate/test_requirements.py::test_no_evidence_not_evaluated` |
| RQ-EVA-015 | `StaticAnalysisTool` | `tests/actions/evaluate/test_static.py::test_lint_detekt_report` |
| RQ-EVA-016 | `ResultStore` | `tests/actions/evaluate/test_eval.py::test_result_persisted` |
| RQ-EVA-017 | `EvaluateAction` resolution | `tests/actions/evaluate/test_eval.py::test_exercise_resolution` |
| RQ-EVA-018 | `EvaluateAction` | `tests/actions/evaluate/test_eval.py::test_build_failure_blocking` |
| RQ-EVA-019 | CLI → `EvaluateAction` | `tests/actions/evaluate/test_eval.py::test_confirmation_required` |
| RQ-EVA-020 | `GradleTool` / `StaticAnalysisTool` / `TestTool` | `tests/actions/evaluate/test_eval.py::test_default_scope` |
| RQ-EVA-021 | `EvaluateAction` + CLI | `tests/actions/evaluate/test_eval.py::test_instrumented_not_run` |
| RQ-EVA-022 | `Rubric` | `tests/actions/evaluate/test_rubric.py::test_rubric_weights` / `test_deterministic_scores` |
| RQ-EVA-023 | CLI → `EvaluateAction` | `tests/actions/evaluate/test_eval.py::test_non_interactive_aborts_without_yes` |
| RQ-EVA-024 | `Rubric` | `tests/actions/evaluate/test_rubric.py::test_subweights_inside_functional_dimension` |
| RQ-EVA-025 | `AttemptStore` | `tests/storage/test_attempts.py::test_mark_completed_after_eval` |
| RQ-EVA-026 | `HistoryStore` | `tests/storage/test_history.py::test_append_evaluation_outcome` |
| RQ-EVA-027 | `EvaluateAction` | `tests/actions/evaluate/test_eval.py::test_persistence_failure_reported` |