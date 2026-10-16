# Spec 0011 — Requirements

## REQ-001 — Action descriptions
The selector SHALL show a concise localized description for every supported student-facing action, explaining its purpose and what the student should do.
**Verification:** enumerate the actual action registry and assert every action has usable descriptions in `es-CO` and `en-US`.

## REQ-002 — Clear activation guidance
The interface SHALL show how to activate the focused action and SHALL provide a clear next-step instruction after selection or execution.
**Verification:** UI/TUI tests cover keyboard navigation, activation, and required-input states.

## REQ-003 — Parameter prompts
Actions requiring further input SHALL display a localized prompt and an example when useful.
**Verification:** tests cover actions with required parameters and missing values.

## REQ-004 — Language selection flow
Selecting Change language SHALL present Spanish and English, explain how to confirm the choice, persist the locale, refresh visible text, and confirm the change.
**Verification:** integration tests verify the full flow and persistence after restart.

## REQ-005 — Progress preservation
Changing locale SHALL NOT reset learning progress, attempts, evidence, exam history, or evaluation results.
**Verification:** before/after state comparison tests.

## REQ-006 — Stage-aware response
Responses SHALL adapt to the resolved current stage and selected action using available context.
**Verification:** tests verify context propagation and stage-appropriate response routing.

## REQ-007 — Evidence-grounded context
The system SHALL NOT invent student history, preferences, mastery, evidence, or project facts.
**Verification:** missing-context tests preserve unknown values.

## REQ-008 — Next-action recommendation
After substantive interactions, the system SHALL determine whether a useful recommendation is justified and SHOULD present one primary recommendation when appropriate.
**Verification:** tests cover useful, unnecessary, and unsupported recommendation cases.

## REQ-009 — Valid recommendations
Recommendations SHALL reference supported action IDs and valid parameters, and include a localized label and brief rationale.
**Verification:** action-registry and schema validation tests.

## REQ-010 — Student agency
Recommendations SHALL NOT execute until explicitly selected. Dismissing them SHALL NOT penalize the student.
**Verification:** interaction tests verify no handler invocation or progression change on display/dismissal.

## REQ-011 — Progression safeguards
Recommendations SHALL NOT change the official stage. Official progression SHALL follow the configured evidence-based policy.
**Verification:** progression regression tests.

## REQ-012 — Bilingual parity
Student-facing action guidance, prompts, results, and recommendations SHALL support `es-CO` and `en-US`. Locale SHALL NOT change scoring or progression.
**Verification:** localization and score-parity tests.

## REQ-013 — Safe failures
Failed actions SHALL NOT be presented as successful. Invalid action definitions, missing translations, or unavailable providers SHALL produce documented diagnostics or safe fallback behavior.
**Verification:** failure-path tests.

## REQ-014 — Reuse existing architecture
The implementation SHALL reuse existing action routing, orchestrator, localization, evaluation, and progression services where available.
**Verification:** integration tests and repository inspection.
