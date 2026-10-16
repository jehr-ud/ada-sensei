# Requirements — 0010 Language Selection

- RQ-LNG-001: Support `es-CO` and `en-US`.
- RQ-LNG-002: Show first-run language selection when no preference exists.
- RQ-LNG-003: Persist the locale across restarts.
- RQ-LNG-004: Allow changing language without resetting learning data.
- RQ-LNG-005: Localize all student-facing content, including stages, rubrics, agents, CLI/TUI, exams and reports.
- RQ-LNG-006: Load and validate locale-specific configuration.
- RQ-LNG-007: Preserve all machine IDs and enums across locales.
- RQ-LNG-008: Use deterministic fallback for missing translations.
- RQ-LNG-009: Pass locale to Teacher, Planner, Evaluator and Trainer.
- RQ-LNG-010: Localization must not alter scoring or progression.
- RQ-LNG-011: Preserve student-authored language and source code.
- RQ-LNG-012: Capture exam locale at `exam-init`.
- RQ-LNG-013: Make language selection keyboard-accessible in CLI/TUI.
- RQ-LNG-014: Test persistence, fallback, locale parity, progression parity and exam report locale.
