# Spec 0011 — Tasks

> OpenCode must reconcile these tasks with the repository's task conventions and only mark completion after verification.

## T1 — Audit and integration
- [x] Read `AGENTS.md` and inspect `specs/`.
- [x] Confirm Spec 0011 is available; do not overwrite existing specs.
- [x] Inspect the real action registry, GUI/TUI selector, handlers, localization, and progress services.
- [x] Preserve Kiro/OpenCode changes and unrelated Git modifications.

## T2 — Action selector guidance
- [x] Ensure every supported student-facing action has localized label, description, activation hint, and parameter metadata where needed.
- [x] Display description for focused/highlighted action.
- [x] Explain keyboard or GUI activation.
- [x] Show clear prompts for actions requiring additional input.
- [x] Test registry coverage and interaction states.

Evidence: `ActionDefinition.outcome_es/outcome_en` + `action_guidance()` in
`ada_sensei/cli/action_registry.py`; `ActionGuide` widget
(`ada_sensei/cli/tui/widgets.py`, `#action-guide` in `styles.tcss`) refreshed
on selection/locale change; empty-input actions emit localized `prereq_*`
prompts instead of silent no-ops. Tests: `tests/tutoring/test_guidance.py`,
`tests/cli/tui/test_tutoring_flow.py`.

## T3 — Change language workflow
- [x] Implement explicit Spanish/English selection.
- [x] Persist and restore locale.
- [x] Refresh visible labels, descriptions, help, and status.
- [x] Confirm language change in the new locale.
- [x] Verify progress and assessment records are preserved.
- [x] Test complete flow.

Evidence: `_pending_language` flow in `ada_sensei/cli/tui/app.py`
(`_start_language_flow`/`_resolve_pending_language`: options `1/2/es-CO/en-US`,
invalid re-prompts, empty cancels); persistence reuses `LocaleService`;
`CommandRouter._language` confirms in the new locale; `_on_worker_done`
refreshes selector/guide/status. Tests: `test_tutoring_flow.py` language cases
+ `tests/locale/test_ui_strings.py` progress-preservation test.

## T4 — Context-aware responses
- [x] Pass current stage, objective, action, locale, and relevant evidence through existing orchestration.
- [x] Route only to necessary subagents.
- [x] Handle missing context safely.
- [x] Add stage/action-aware tests.

Evidence and note: `AgentContext.stage_objective` (optional, `None` when
unknown) resolved from the locale catalog in `TeacherAgent`; planner gaps feed
`TutorContext`. Routing note: spec 009's mandatory invocation rule (all three
specialists participate once per action) takes precedence over the design
suggestion to route "only to necessary subagents", so orchestration still
invokes Planner/Evaluator/Trainer exactly once — context-aware adaptation
happens via the shared `AgentContext` and the deterministic recommender, not
by skipping specialists. Tests: `test_teacher_agent.py` (objective
propagation), `tests/tutoring/test_guidance.py` (unknown stays unknown).

## T5 — Next-action recommendations
- [x] Generate one useful recommendation when justified.
- [x] Validate action IDs, parameters, and prerequisites.
- [x] Display recommendation and rationale in selected locale.
- [x] Execute only after explicit student selection.
- [x] Test no-recommendation, dismissal, invalid recommendation, and recovery paths.

Evidence: `ada_sensei/tutoring/` (`context.py`, `recommender.py` priority
rules, `Recommendation.display()`); `TeacherAgent` appends the validated block
to `final_response`; `CommandRouter.suggest_next()` + TUI `_emit_recommendation`
render it or a neutral invite; display never dispatches (ignoring is safe).
Tests: recommender sweep/validation/agency cases + TUI no-auto-execution test.

## T6 — Progression safeguards
- [x] Reuse the existing evidence-based progression policy.
- [x] Ensure recommendation generation/dismissal does not mutate stage or mastery.
- [x] Test missing evidence and progression regressions.

Evidence: recommender is pure (no stores, no LLM); full suite green including
`tests/learning/test_stage_status.py` and progression tests; new tests assert
profile unchanged after recommend/display/dismiss cycles.

## T7 — Documentation and verification
- [x] Update related existing specs/ADRs without creating duplicates.
- [x] Run relevant tests, linting, type checks, and formatting.
- [x] Record actual results and remaining blockers.
- [x] Mark tasks complete only with evidence.

Evidence: full suite `519 passed`; `ruff check . --fix` (see final report);
no spec text overwritten — only these task checkboxes updated. Related
existing spec touched: none required (0011 already defines behavior; 002-cli
registry/TUI contracts unchanged and compatible).

## Definition of done
- [x] Every supported selector action explains itself in both locales.
- [x] Change language is a clear, working flow.
- [x] Actions either produce a result or explain the next required input.
- [x] Useful contextual recommendations are available after substantive interactions.
- [x] Recommendations are optional and cannot advance the stage.
- [x] Tests and specs agree with the implementation.
