# 0010 — Language Selection and Localization

## Status
Specification update: interactive language selector for the existing CLI/TUI action menu.

## Purpose
Allow a student to change the ADA Sensei interface language directly from the action selector. When the student highlights and activates `Change language`, ADA Sensei SHALL display the supported languages as a navigable list. The student SHALL be able to move the cursor, choose a language, and confirm the choice without typing a locale code.

## Supported locales
- `es-CO`, displayed as **Español**.
- `en-US`, displayed as **English**.

The visible names are localized/product labels; the locale codes remain stable internal identifiers.

## User story
As a student using the terminal interface, when I select `Change language`, I see the available languages in a selectable list, can move the cursor with the keyboard, and can confirm my choice. The interface then changes language and preserves my learning progress.

## Requirements

### RQ-LNG-001 — Supported languages
The application SHALL support `es-CO` and `en-US`, displayed as `Español` and `English`.

### RQ-LNG-002 — First-run selection
If no language preference exists, show a language-selection screen before onboarding. The student must explicitly confirm a language to continue.

### RQ-LNG-003 — Persist preference
Persist the selected locale, source, and update timestamp in the existing student profile/settings. The preference SHALL survive application restart.

### RQ-LNG-004 — Change language from action selector
When the student activates `Change language`, the application SHALL enter a dedicated language-selection state/screen. It SHALL NOT merely highlight the action or return to a generic prompt.

### RQ-LNG-004b — Selector/welcome parity
The action-selector flow and the first-run welcome flow SHALL present the same language list: the same supported options from the single locale definition, the same cursor/focus marker, the same visible key hints, and the same confirm/cancel semantics. The welcome flow additionally blocks onboarding until an explicit choice is confirmed; the selector flow returns to the action selector instead.

### RQ-LNG-005 — Cursor navigation
The language list SHALL be keyboard navigable:
- `Up` / `Down` (or the terminal framework's equivalent) moves the cursor between supported languages.
- The focused language SHALL be visually distinguishable.
- `Enter` confirms the focused language.
- `Esc` / `q` cancels and returns to the action selector without changing the saved locale.
- If the TUI framework uses different conventions, the interface SHALL show its actual keys visibly.

### RQ-LNG-006 — Immediate visible feedback
After confirmation, persist the locale, refresh the visible interface text (action labels/descriptions, prompts, help, status bar, and messages), and show a confirmation in the newly selected language. The selected language SHALL become active immediately without requiring a restart.

### RQ-LNG-007 — Preserve learning data
Changing language SHALL NOT reset or mutate the student's stage, mastery, attempts, learning plan, assessment evidence, evaluation results, or exam history. It SHALL only update locale preference metadata.

### RQ-LNG-008 — Localize all student-facing content
All student-facing static text and agent output SHALL use the selected locale where translations exist, including onboarding, stages, rubrics, action selector, input hints, errors, practice, examples, evaluation feedback, exam prompts, and reports.

### RQ-LNG-009 — Config and locale validation
Use the existing locale-aware config/localization loader. Validate the saved or selected locale against supported locale IDs. Do not use translated labels as identifiers.

### RQ-LNG-010 — Stable semantics
Locale changes SHALL NOT alter stage/rubric/criterion IDs, score values, weights, critical flags, evidence requirements, progression thresholds, or decisions.

### RQ-LNG-011 — Deterministic fallback
Missing translations SHALL use the documented deterministic fallback and emit diagnostics. Do not ask the LLM to invent critical rubric criteria or scoring rules.

### RQ-LNG-012 — Agent propagation
The active locale SHALL be passed through TeacherAgent, PlannerAgent, EvaluatorAgent, and TrainerAgent. Machine-readable fields remain language-neutral.

### RQ-LNG-013 — Exam locale snapshot
`exam-init` SHALL record the locale used for the attempt; `exam-finish` SHALL use that locale for its report even if the profile locale changes later.

### RQ-LNG-014 — Tests
Automated tests SHALL verify:
- The `Change language` action opens the language list.
- Cursor navigation changes the focused language.
- Enter saves the selected locale and updates visible text immediately.
- Escape/cancel preserves the previous locale.
- The selected locale survives restart.
- Learning state is unchanged by language selection.
- Both locales preserve stable IDs and scoring/progression semantics.
- Exam reports use the locale captured at exam start.

### RQ-LNG-015 — Selector Enter opens the shared language list

Regression: activating `Change language` from the action selector only updated
the action description/input area and never opened the language list, because
the base dropdown consumes Enter for its overlay. The fix SHALL intercept Enter
while the selector is focused by matching the committed option's stable action
id (`language`), never its localized label, and open the exact same
`LanguageList` widget and selection state machine used by first-run welcome
(same options, cursor, hints, Up/Down/Enter/Esc/q behavior). Opening or
cancelling from the selector SHALL NOT dispatch ordinary free text to
TeacherAgent. Acceptance: dedicated regression tests prove selector-Enter
opening, shared-widget reuse, saved-locale focus, confirm/cancel semantics,
and no agent dispatch; existing welcome selection still works.

## Design

### Preference model
```json
{
  "locale": "es-CO",
  "locale_source": "student_selection",
  "updated_at": "ISO-8601 timestamp"
}
```
`locale_source` SHALL be one of `student_selection`, `configured_default`, or `migration`.

### Interaction flow
```text
Action selector
  -> focus "Change language"
  -> Enter
  -> Language list:
       > Español
         English
  -> Up/Down to move cursor
  -> Enter to confirm
  -> Persist locale
  -> Refresh localized UI
  -> Show confirmation in selected language
  -> Return to action selector (or continue to onboarding if first run)
```

### Cancellation
Escape/q cancels the flow without writing preference changes. On first run, cancellation SHALL return to the language list or keep onboarding blocked until the student makes an explicit choice; it SHALL not silently assign the configured default as a student choice.

### Architecture
Reuse the existing action registry, TUI framework, localization service, locale preference store, and config loader. The UI should invoke a language-selection action/handler; it should not implement persistence or localization logic itself. Avoid a separate hardcoded list in each UI.

### Test strategy
Use the existing TUI interaction test framework or test the language-selection state machine separately. Verify cursor focus, confirmation, cancellation, immediate refresh, persistence, and learning-state invariants.


## Regression fix — Reuse the welcome language selector from the action menu

The existing first-run welcome flow already displays the `LanguageList` selector. The `Change language` action MUST open that same interactive selector, not merely change the selected action's input hint or display its description.

### Required behavior

1. When the action selector's current action is `Change language` (stable action id `language`) and the user presses Enter, open the same `LanguageList` UI used during first-run language selection.
2. The list MUST be visible in the main TUI, with heading `Select language / Selecciona el idioma`, supported options `Español` and `English`, a visible cursor/focus marker, and keyboard hints.
3. Up/Down moves the language cursor; Enter confirms; Esc/q cancels. Follow the bindings shown by the existing widget.
4. Initially focus the currently saved locale.
5. On confirmation, persist the locale, refresh localized UI immediately, and return to the action selector. Preserve student identity, learning progress, selected stage, evaluation history, and exam history.
6. On cancellation, return to the action selector without changing the saved locale.
7. Do not dispatch `Change language` as ordinary free text to TeacherAgent or treat the action's description as the language-selection result.
8. First-run welcome and action-menu entry points MUST use the same widget, locale options registry, and selection state machine. Do not implement a second language selector.

### Acceptance test

With an existing profile and saved locale `en-US`:
- Select `Change language` in the action selector and press Enter.
- The language list is visibly rendered, with `English` initially focused.
- Press Up or Down to change focus and press Enter.
- The saved locale and visible UI update; the TUI returns to the action selector.
- Press Esc instead and verify the saved locale remains `en-US`.
