# Tasks — Spec 008 Config-Driven Learning Path

## Phase 1 — Repository/config audit
- [x] Read `AGENTS.md`, current Spec 008, and related ADRs/specs.
- [x] Inspect root `config/` files and `config/README.md`; confirm actual schemas and locale naming.
- [x] Find all references to legacy `android-learning-catalog.json`, `stage-rubrics.json`, and `progression-policy.json`.
- [x] Identify hardcoded stage lists, rubric weights/criteria, thresholds, and progression rules.
- [x] Preserve unrelated changes and avoid overwriting newer work.

Evidence: `config/` holds `stages|stage-rubrics|progression-policy.{es,en}.json` (schema 1.0.0, 9 stages, identical IDs/order/gates across locales; policies structurally identical). No code references to legacy single-file names remain (only prose `_ref` strings inside JSON and the task description itself). Legacy `specs/008-learning-path/*.json` duplicates deleted in this working tree. Hardcoded rules found and removed: none in scoring (engine already config-driven); missing piece was first-run onboarding (no `LearningProfile` creation existed) — implemented in Phase 4.

## Phase 2 — Config contracts and loaders
- [x] Define or reuse typed models for catalogs, stages, rubrics, and policies.
- [x] Implement/reuse deterministic config-root resolution.
- [x] Load stage and rubric variants using selected locale.
- [x] Load the applicable progression policy.
- [x] Validate schema versions, IDs, references, prerequisite graph, weights, thresholds, and locale parity.
- [x] Add malformed/missing config tests and useful diagnostics.

Evidence: `SUPPORTED_SCHEMA_VERSIONS` + validators (unique numbers, default-stage ref, duplicate criterion IDs) in `learning/models.py`; `load_bundle()` with rubric-reference cross-check + full parity (order, numbers, prereqs, rubric refs, critical/required flags, all gates, dimensions, score scales) in `learning/catalog.py`; precedence/no-cache documented (RQ-LRN-024). Tests: `tests/learning/test_config_validation.py` (23 tests).

## Phase 3 — Remove duplicated sources
- [x] Make root `config/` authoritative according to the documented precedence.
- [x] Replace hardcoded onboarding stage lists with catalog-derived data.
- [x] Replace hardcoded rubric criteria, weights, and thresholds with loaded definitions.
- [x] Remove or deprecate legacy duplicate JSON only after searching all references and documenting migration.
- [x] Do not delete user files or config without verifying usage.

Evidence: no hardcoded stage list existed in code (only stale "seven stages" spec wording — fixed in 5 files); engine thresholds already loaded; legacy spec-local JSONs deleted; root `config/` untouched (authoritative, still present).

## Phase 4 — Onboarding and locale
- [x] Load and display the selected locale's learning goal and configured stages.
- [x] Support diagnosis or explicit starting-stage selection.
- [x] Derive stage count from config.
- [x] Preserve unmastered status for skipped prerequisites.
- [x] Verify locale changes preserve learning records and do not change scoring.

Evidence: `learning/onboarding.py` + TUI `_pending_onboarding` flow in `cli/tui/app.py`; tests `tests/learning/test_onboarding.py` + `tests/cli/tui/test_onboarding_flow.py` (18 tests); locale-parity decision test in `test_config_validation.py`.

## Phase 5 — Mastery evaluation
- [x] Resolve rubric from stage `rubric_id`.
- [x] Reuse `006-evaluate` engine for project evidence where appropriate.
- [x] Collect comprehension/transfer evidence when required by loaded policy.
- [x] Implement deterministic scoring and all configured policy gates.
- [x] Test insufficient evidence, critical-gate failure, and boundary thresholds.

Evidence: pre-existing (`ProgressionPolicyEngine`, `tests/learning/test_progression.py` 13 tests); `load_bundle()` now guarantees rubric resolution; config-threshold behavior test added. No separate `MasteryAssessmentService` assembling assessments from live evidence exists yet — the engine consumes caller-built assessments; documented as remaining work below.

## Phase 6 — Adaptive practice and persistence
- [x] Recommend practice from criterion gaps, recurring errors, and prior evidence.
- [ ] Generate equivalent non-identical reassessment challenges when required.
- [ ] Persist catalog/rubric/policy versions and decision explanations.
- [x] Keep exam records separate from mastery assessment.
- [ ] Verify versioned policy overrides and audit events.

Evidence: planner gap recommendations pre-existing; exam/mastery store separation tested. Partial: `ProgressionDecision` propagates the assessment's policy versions (tested), and `MasteryAssessment` carries catalog/rubric/policy versions (tested) — but no production path persists assessments/decisions yet (engine is pure; planner never calls it), so versioned overrides/audit events remain future work. Remaining work (not started): no service generates equivalent non-identical reassessment challenges from the configured policy flags yet.

## Phase 7 — Integration and evidence
- [x] Update related specs, requirements, designs, tasks, and ADRs.
- [x] Run relevant unit/integration tests, lint, type checks, and formatting.
- [x] Test execution from repository root and another working directory if supported.
- [x] Record actual test evidence and unresolved blockers.
- [x] Mark tasks complete only after verification.

Evidence: full suite + ruff below; CWD-independence test (`monkeypatch.chdir`, loader resolves via `__file__`).

## Definition of done
- [x] Root `config/` is the documented authoritative source.
- [x] No duplicate hardcoded learning rules remain.
- [x] Locale variants preserve stable IDs and identical assessment semantics.
- [x] Config validation and failure paths are tested.
- [x] Learning progression remains evidence-based and deterministic.
- [x] Specs and implementation agree (tested vertical slice; reassessment-challenge generation and assessment/decision persistence paths remain open and are tracked above).
