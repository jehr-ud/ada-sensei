# Requirements — 0010 Interactive Language Selector

- RQ-LNG-001: Support `es-CO` and `en-US`, displayed as `Español` and `English`.
- RQ-LNG-002: Require explicit language selection on first run.
- RQ-LNG-003: Persist locale preference across restarts.
- RQ-LNG-004: Activating `Change language` opens a dedicated selectable language list.
- RQ-LNG-004b: Selector and welcome flows share the same language list (options, cursor, hints, confirm/cancel semantics).
- RQ-LNG-005: Up/Down moves the cursor; Enter confirms; Escape/q cancels without changing the saved locale. Actual key bindings must be visible.
- RQ-LNG-006: On confirmation, update saved locale and refresh visible text immediately.
- RQ-LNG-007: Preserve learning stage, mastery, attempts, plan, evidence, evaluations, and exam history.
- RQ-LNG-008: Localize all student-facing content and agent output.
- RQ-LNG-009: Validate locale IDs and reuse the existing localization/config loader.
- RQ-LNG-010: Locale must not affect IDs, scoring, weights, gates, evidence, or progression.
- RQ-LNG-011: Use deterministic translation fallback and diagnostics.
- RQ-LNG-012: Propagate active locale to Teacher, Planner, Evaluator, and Trainer.
- RQ-LNG-013: Snapshot locale at exam start and use it for the exam report.
- RQ-LNG-014: Test selection, navigation, confirmation, cancellation, persistence, refresh, progress preservation, locale parity, and exam report locale.
- RQ-LNG-015: Enter on the focused action selector with stable id `language` opens the shared language list (same widget/state machine as welcome); no free-text dispatch to TeacherAgent.


## RQ-LNG-015 — Change-language action opens the shared selector

When the user activates the `Change language` action from the main TUI action selector, the TUI SHALL display the same interactive `LanguageList` widget used by first-run welcome selection. Displaying only the action description, placeholder, or generic input area SHALL NOT satisfy this requirement. The saved locale SHALL be focused initially. Confirmation SHALL persist and apply the selected locale and return to the action selector; cancellation SHALL leave the locale unchanged. This flow SHALL NOT dispatch the action as ordinary free text to the TeacherAgent.

Automated tests SHALL verify that the selector widget is mounted/visible on activation, keyboard navigation and confirmation work, cancellation preserves the locale, and first-run and action-menu flows share the same selector implementation.
