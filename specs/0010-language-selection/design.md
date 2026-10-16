# Design — 0010 Interactive Language Selector

## Preference
Persist `locale`, `locale_source`, and `updated_at` in the existing student settings/profile.

## TUI interaction
When the user activates `Change language`, transition to a dedicated language-selection state. Render a list with `Español` and `English`, a visible cursor/focus marker, and a help line describing the available keys.

Expected default interaction:
- Up/Down: move focus.
- Enter: confirm.
- Esc or q: cancel.
If the existing TUI framework has different standard bindings, use those and display them clearly.

Example:
```text
Select language / Selecciona el idioma

  > Español
    English

  ↑/↓ Move   Enter Select   Esc Cancel
```

The cursor initially focuses the currently saved locale when one exists. On first run, a configurable default may be focused, but the UI must still require explicit confirmation.

## Apply selection
On Enter:
1. Map the focused display item to stable locale ID (`es-CO` or `en-US`).
2. Validate the locale ID.
3. Persist the locale preference.
4. Refresh action labels, descriptions, prompts, help, status bar, and subsequent agent responses.
5. Confirm the change in the newly selected language.
6. Return to the action selector, or continue onboarding if this is first-run selection.

On cancel, do not persist changes. First-run onboarding must still require an explicit choice.

## Architecture
Reuse existing action registry, TUI framework, locale store, localization service, and config loader. UI code invokes a handler; it does not own persistence or translation logic. Do not create duplicate language lists in multiple interfaces.

Implementation mapping: both entry points (`Change language` from the action selector and the first-run gate before onboarding) open the same `LanguageList` widget driven by the same `LanguageSelection` cursor state over the single `LOCALE_LABELS`/`LOCALE_OPTIONS` definition. The only difference is continuation: selector flow returns to the action selector, first-run flow continues to onboarding after the write succeeds; first-run cancellation keeps the gate open instead of closing the list.

### Selector Enter interception (RQ-LNG-015)
The base Textual `Select` consumes Enter to toggle its overlay, so Enter on the focused selector never reached submission and the list never opened from the action menu. Selecting the `Change language` action now opens the shared list automatically with no extra Enter required; additionally, `ActionSelector` (a `Select` subclass in `cli/tui/widgets.py`) intercepts a later Enter press only when the committed option value's stable id is `language` — never the localized label — and posts `LanguageRequested`, which refocuses the already-open list. All other values keep native dropdown behavior, and the input-area Enter path (`LanguageCommand` without locale) is unchanged.

Implementation mapping: both entry points (`Change language` from the action selector and the first-run gate before onboarding) open the same `LanguageList` widget driven by the same `LanguageSelection` cursor state over the single `LOCALE_LABELS`/`LOCALE_OPTIONS` definition. The only difference is continuation: selector flow returns to the action selector, first-run flow continues to onboarding after the write succeeds; first-run cancellation keeps the gate open instead of closing the list.

## Invariants
- Locale IDs: `es-CO`, `en-US`.
- IDs, scores, weights, critical flags, evidence requirements, and progression decisions are locale-independent.
- Missing translations use deterministic fallback and diagnostics.
- Language switching does not mutate learning state.
- `exam-init` snapshots locale for a consistent `exam-finish` report.

## Testing
Test navigation/focus, Enter confirmation, cancellation, first-run behavior, saved-locale focus, persistence/restart, immediate UI refresh, learning-state immutability, locale parity, and exam locale snapshot.

## First-run UI
A compact screen with `Español` and `English`. After selection, show the welcome objective, all configured stages from the active catalog, and the choices to run a diagnostic or select a starting stage.

## Regression fix — Action-menu language selector wiring (RQ-LNG-015)

The welcome flow and the action-selector flow must call one shared function/handler to open `LanguageList`. The action-selector handler for stable action id `language` must intercept Enter before ordinary free-text routing or agent dispatch.

Expected state transition:

```text
ActionSelector(action_id="language")
  -- Enter -->
LanguageList(current_locale=LocalePreferenceStore.load())
  -- Up/Down -->
LanguageList(updated_focus)
  -- Enter -->
LocaleService.set_locale(focused_locale)
  --> refresh localized UI
  --> return focus to ActionSelector
```

Cancellation:

```text
LanguageList -- Esc/q --> close list without writing preference
                         --> return to ActionSelector
```

Implementation checks:
- Reuse `LanguageList`, `LanguageSelection`, `LOCALE_OPTIONS`, and the existing locale service/store if present.
- Verify that the action handler is actually invoked by the selector's Enter event. A localized action label or input placeholder is not an implementation.
- Keep language-list rendering independent of first-run-only onboarding logic.
- Do not add duplicate locale options or a second widget.
- Preserve the current action selector value, conversation history, student identity, and learning state.
- Ensure focus is returned to the appropriate control after confirmation/cancellation.
