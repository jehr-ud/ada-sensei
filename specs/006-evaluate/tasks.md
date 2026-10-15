# Tasks

## Phase 1 — Evaluation domain and reusable contracts

- [x] Review existing foundation evidence/model contracts.
- [x] Define `EvidenceContext`.
- [x] Define `RubricDefinition`.
- [x] Define versioned `EvaluateRubricDefinition`.
- [x] Define reusable `EvaluationEngine` contract.
- [x] Define deterministic `ScoreBreakdown` contract.

## Phase 2 — Evidence collection

- [x] Implement/refine `AndroidProjectAnalyzer`.
- [x] Implement/refine `GradleTool`.
- [x] Implement/refine `TestTool`.
- [x] Implement/refine `StaticAnalysisTool`.
- [x] Preserve ERROR/WARNING/INFO severity.
- [x] Preserve evidence provenance and limitations.

## Phase 3 — Requirement matching

- [x] Implement/refine `RequirementMatcher`.
- [x] Map evidence to `req://` identifiers.
- [x] Preserve unmatched evidence.
- [x] Mark unsupported criteria as `not_evaluated`.

## Phase 4 — Rubric engine

- [x] Implement generic `RubricEngine`.
- [x] Validate top-level weights sum to 1.0.
- [x] Validate functional subweights sum to 1.0.
- [x] Implement 0–4 criterion/dimension scoring.
- [x] Implement deterministic 0–100 normalization.
- [x] Exclude `not_evaluated` dimensions according to the evidence policy.
- [x] Add versioned `evaluate-default:v1`.
- [x] Verify 40/20/15/15/10 weights.
- [x] Ensure other workflows cannot mutate the evaluate rubric.

## Phase 5 — Evaluation agent

- [x] Define structured `EvaluationResult` schema.
- [x] Define evidence-reference requirements for LLM claims.
- [x] Implement structured parser.
- [x] Implement schema validation.
- [x] Implement maximum 3 total attempts: initial + up to 2 retries.
- [x] Fail explicitly after validation failure.
- [x] Reject or flag unsupported evidence claims.

## Phase 6 — Evaluation orchestration

- [x] Implement `EvaluationEngine.collect_evidence()`.
- [x] Implement `EvaluationEngine.evaluate()`.
- [x] Refactor `EvaluateAction` to orchestrate the reusable engine.
- [x] Preserve exercise resolution.
- [x] Preserve confirmation before Gradle.
- [x] Preserve `--yes` non-interactive behavior.
- [x] Preserve no `connectedAndroidTest` behavior.
- [x] Preserve read-only project policy.

## Phase 7 — Persistence and history

- [x] Persist `EvaluationResult`.
- [x] Bind results to `student_id`, `project_id`, `exercise_id`, `attempt_id`.
- [x] Mark known attempts completed after successful evaluation.
- [x] Append outcome to `HistoryStore`.
- [x] Report persistence failures explicitly.

## Phase 8 — Tests

- [x] Test reusable evaluation engine.
- [x] Test evidence context independence from `/evaluate`.
- [x] Test reusable requirement matcher.
- [x] Test rubric definition validation.
- [x] Test evaluate rubric isolation.
- [x] Test deterministic scoring.
- [x] Test not-evaluated behavior.
- [x] Test structured-output 3-attempt limit.
- [x] Test unsupported-claim handling.
- [x] Test external workflow reuse.
- [x] Test build success.
- [x] Test build failure.
- [x] Test missing tool/evidence.
- [x] Test confirmation.
- [x] Test non-interactive `--yes`.
- [x] Test instrumented-test rejection.
- [x] Test persistence failures.

## Phase 9 — Integration fixture

- [x] Maintain a sample Android fixture project.
- [x] Add successful evaluation integration test.
- [x] Add failed-build integration test.
- [x] Add static-analysis evidence fixture.
- [x] Add requirement-matching fixture.

## Phase 10 — 007-examine compatibility

- [x] Add an integration test proving `007-examine` can consume `EvaluationEngine`.
- [x] Verify `007-examine` can provide a distinct rubric definition.
- [x] Verify `007-examine` cannot mutate `evaluate-default:v1`.
- [x] Verify evidence collection is not duplicated.