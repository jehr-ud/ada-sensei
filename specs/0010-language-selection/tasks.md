# Tasks — 0010 Interactive Language Selector

- [x] Inspect `AGENTS.md`, the existing Spec 0010, action registry, TUI framework, locale store, and localization loader.
- [x] Implement the language-selection state/screen opened by `Change language`.
- [x] Render `Español` and `English` as cursor-selectable options.
- [x] Implement visible keyboard navigation and confirmation/cancellation hints.
- [x] Focus the saved locale initially; require explicit confirmation on first run.
- [x] Persist locale selection using existing profile/settings storage.
- [x] Refresh visible localized UI immediately after confirmation.
- [x] Preserve learning/progression/evaluation/exam data.
- [x] Ensure locale propagation through Teacher, Planner, Evaluator, and Trainer.
- [x] Preserve exam locale snapshot behavior.
- [x] Add tests for cursor movement, selection, cancellation, persistence, refresh, and invariants.
- [x] Run relevant tests and record actual results.
- [x] Update related specs/ADRs without creating duplicate language-selection implementations.

Evidence: `LanguageSelection` state machine (`locale/selection.py`) over the
single `LOCALE_LABELS`/`LOCALE_OPTIONS` definition (`locale/models.py`);
`LanguageList` widget (`cli/tui/widgets.py`, `#language-list`) with
widget-scoped Up/Down/Enter/Esc/q bindings, `>` cursor and hints line;
app wiring (`cli/tui/app.py`: open on `Change language`+Enter, saved-locale
focus, first-run gate before onboarding, cancel semantics, immediate refresh
via existing worker-done path); exam snapshot (`ExamAttempt.locale`,
`ExamResult.locale`, lifecycle/start/finish, report `Language:` line).
Tests: `tests/locale/test_selection_state.py` (9),
`tests/cli/tui/test_language_selection.py` (13, incl. selector/welcome
parity RQ-LNG-004b),
`tests/exams/test_exam_locale.py` (3),
`tests/lang/test_locale_propagation.py` (2); full suite 560+ passed, ruff clean
of new non-E501 findings. No duplicate subsystem: persistence via
`LocaleService`/`LocalePreferenceStore`, refresh via existing paths.


## Regression phase — Shared language selector from action menu (RQ-LNG-015)

- [x] Reproduce the reported defect: selecting `Change language` currently changes the action/description but does not show the language list.
- [x] Trace the selector Enter event and verify stable action id `language` invokes the language-selection handler rather than ordinary free-text dispatch.
- [x] Wire the action-menu entry point to the same `LanguageList` widget/state machine used by first-run welcome.
- [x] Focus the saved locale when the list opens.
- [x] Verify the list is visibly mounted and displays both supported locales and keyboard hints.
- [x] Verify Up/Down navigation, Enter confirmation, and Esc/q cancellation.
- [x] Verify confirmation updates locale and visible text immediately, then returns to the action selector.
- [x] Verify cancellation leaves the saved locale unchanged.
- [x] Add regression tests for action-menu opening, shared widget reuse, focus, confirmation, cancellation, and no agent dispatch.
- [x] Run focused locale/TUI tests and the relevant full suite; record actual results.
- [x] Mark tasks complete only when implementation and test evidence exist.

Evidence (RQ-LNG-015): root cause — base `Select` consumes Enter for its
overlay, so Enter on the focused selector never submitted. `ActionSelector`
(`cli/tui/widgets.py`) intercepts Enter only when the committed value is the
stable id `language` and posts `LanguageRequested`; `AdaSenseiTUI` opens the
shared list (`cli/tui/app.py`). Other values keep native behavior; the
input-area path is unchanged. Tests: 5 new in
`tests/cli/tui/test_language_selection.py` (open, stable-id-under-es-labels,
native-behavior preserved, full keyboard confirm with state preservation,
no-dispatch spy); suite results below.
