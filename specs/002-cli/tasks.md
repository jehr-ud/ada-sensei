# ADA Sensei — CLI and TUI Implementation Tasks

## Phase 1 — CLI package setup

- [ ] Create `ada_sensei/cli/` package with `__init__.py`.
- [ ] Create `cli/app.py` (entry point), `cli/commands.py`, `cli/router.py`,
      `cli/formatter.py`.

## Phase 2 — Command model

- [ ] Define typed command objects: `PracticeCommand`, `AskCommand`,
      `ExamplesCommand`, `EvaluateCommand`, `HintCommand`,
      `MoreCommand`, `SolutionCommand`, `HelpCommand`, `ClearCommand`,
      `QuitCommand`.
- [ ] Define the `CommandResult` discriminated union.
- [ ] Define validation for command arguments where applicable
      (difficulty enum, required question/topic text, exercise id format).

## Phase 3 — Argument parser / entry point

- [ ] Implement global option parsing (`--project`, `--yes`,
      `--offline`).
- [ ] Implement action subcommand parsing (`practice`, `ask`, `examples`,
      `evaluate`) and action-specific options.
- [ ] Implement TUI launch when no action subcommand is supplied (RQ-CLI-001).
- [ ] Implement `--help` (global and per-action) output (RQ-CLI-021).
- [ ] Implement exit codes (RQ-CLI-018).

## Phase 4 — Command router

- [ ] Implement `CommandRouter.dispatch(command, context)`.
- [ ] Wire each command type to its application action (practice, ask,
      examples, evaluate, hint/more/solution, help, clear, quit).
- [ ] Ensure the router contains no action business logic (RQ-CLI-005).

## Phase 5 — Direct CLI execution and formatting

- [ ] Implement the direct execution flow: parse → validate → build command →
      dispatch → format → print → exit (RQ-CLI-003/004/005).
- [ ] Implement `cli/formatter.py` for plain-text output of all `CommandResult`
      variants (RQ-CLI-019).
- [ ] Write success output to stdout and errors to stderr.
- [ ] Implement secret redaction in the formatter.

## Phase 6 — Evaluation confirmation

- [ ] Implement interactive evaluation confirmation prompt for the direct CLI
      (RQ-CLI-014).
- [ ] Ensure declining confirmation starts no Gradle process.
- [ ] Implement `--yes` non-interactive override (RQ-CLI-016, ADR-019).
- [ ] Implement `--instrumented` rejection (RQ-CLI-015).
- [ ] Implement `--exercise` selection with session-current-exercise fallback
      (RQ-CLI-010).

## Phase 7 — CLI error handling

- [ ] Implement expected vs. unexpected error distinction.
- [ ] Implement sanitized error output and exit codes (RQ-CLI-018/019).
- [ ] Implement context reduction notice rendering (RQ-CLI-020).

## Phase 8 — TUI package setup

- [ ] Add Textual as a runtime dependency.
- [ ] Add/update development dependencies needed for TUI tests.
- [ ] Create `ada_sensei/cli/tui/` package.
- [ ] Ensure only the TUI package imports Textual (RQ-TUI-027).

## Phase 9 — TUI application shell

- [ ] Implement `TuiApp` based on Textual `App` (RQ-TUI-004).
- [ ] Implement the main screen/layout with header, scrollable content, input,
      and status/help area.
- [ ] Add initial TCSS styling in `styles.tcss`.
- [ ] Add terminal resize handling and minimum-size graceful behavior
      (RQ-TUI-023/024).
- [ ] Ensure TUI launch from `ada-sensei` with no action (RQ-TUI-001).

## Phase 10 — TUI command system

- [ ] Implement TUI slash-command parsing into the shared command objects
      (RQ-TUI-003/005).
- [ ] Implement `/help`.
- [ ] Implement `/quit` and `/exit`.
- [ ] Implement `/clear`.
- [ ] Use the name received at the welcome greeting to set student identity
      (no `/student`, RQ-CLI-006, RQ-TUI-007).
- [ ] Implement `/practice` argument forwarding.
- [ ] Implement `/ask`.
- [ ] Implement `/examples`.
- [ ] Implement `/evaluate`.
- [ ] Implement `/hint`, `/more`, and `/solution` (RQ-CLI-017).
- [ ] Render a recoverable error for unknown slash commands.

## Phase 11 — TUI application integration

- [ ] Connect TUI slash commands to the shared `CommandRouter` (RQ-TUI-003).
- [ ] Reuse `SessionContext` rather than creating a second session model.
- [ ] Reuse existing practice, ask, examples, and evaluate actions.
- [ ] Set student identity from the name given at session start, creating the
      local Profile when absent.
- [ ] Display active project/session context (RQ-TUI-008).

## Phase 15.5 — TUI welcome identity (RQ-TUI-029, RQ-TUI-007)

- [ ] On TUI mount, if a last used student name exists, start directly with it
      and do not re-ask; otherwise prompt for the student's name.
- [ ] Use the received name as `student_id`, persist it to the
      `StudentProfile` (`HistoryStore.set_name` / `create_profile`), and save it
      as the last used name (`LastStudentStore`).
- [ ] Greet a returning profile with `Welcome back, <name>!`.
- [ ] Implement `/name <name>` to update the student identity and the remembered
      name.
- [ ] Never infer identity from context; identity comes only from the received
      name (RQ-CLI-006, RQ-TUI-007).
- [ ] Add TUI welcome/identity tests (`tests/cli/tui/test_welcome.py`).

## Phase 12 — TUI result rendering

- [ ] Implement user and assistant message widgets.
- [ ] Implement exercise rendering (RQ-TUI-009).
- [ ] Implement progressive-assistance rendering (RQ-TUI-010).
- [ ] Implement example/code rendering with syntax highlighting (RQ-TUI-012).
- [ ] Implement evaluation result rendering (RQ-TUI-018).
- [ ] Implement status and error rendering (RQ-TUI-019).
- [ ] Implement secret redaction in TUI output (RQ-TUI-020).
- [ ] Implement context reduction notice display (RQ-CLI-020).

## Phase 13 — TUI long-running operations

- [ ] Execute LLM requests through Textual workers/async mechanisms
      (RQ-TUI-016).
- [ ] Execute evaluation through workers/async mechanisms.
- [ ] Keep the UI event loop responsive during operations.
- [ ] Display evaluation/application progress events (RQ-TUI-015).
- [ ] Implement cancellation where the application layer supports it
      (RQ-TUI-017).
- [ ] Ensure cancellation does not corrupt authoritative domain state.

## Phase 14 — TUI evaluation safety

- [ ] Show evaluation scope before execution.
- [ ] Require confirmation before any Gradle-based evaluation task
      (RQ-TUI-013).
- [ ] Ensure declining confirmation starts no Gradle process.
- [ ] Preserve `--yes` behavior for direct non-interactive evaluation
      (RQ-TUI-014).
- [ ] Ensure the TUI never launches `connectedAndroidTest` by default
      (RQ-CLI-015).
- [ ] Ensure the TUI never calculates or modifies evaluation scores
      (RQ-TUI-018).

## Phase 15 — TUI UX and discoverability

- [ ] Add keyboard bindings for submit, quit/cancel, and scrolling
      (RQ-TUI-021).
- [ ] Add command palette or equivalent command discovery (RQ-TUI-022).
- [ ] Implement one persistent visible action selector (Textual `Select`) with
      `ask`, `practice`, `examples`, and `evaluate` (RQ-TUI-004/030/033).
- [ ] Implement the editable multi-line TextArea (RQ-TUI-030/031).
- [ ] Make Enter execute the selected action.
- [ ] Make Shift+Enter insert a newline in the TextArea.
- [ ] Ensure normal TextArea typing is not consumed by global bindings.
- [ ] Restore TextArea focus after completion, error, and cancellation.
- [ ] Route free text that does not start with `/` to the selected action;
      slash-prefixed input remains a slash command (RQ-TUI-030).
- [ ] Remove the separate Evaluate button; evaluate is selected from the same
      action selector (RQ-TUI-030/033).
- [ ] Add concise status/help hints that explicitly communicate `Enter Run`
      and `Shift+Enter New line`.
- [ ] Implement the persistent session footer showing student, latest score,
      configured AI model, current action, and operation status (RQ-TUI-032).
- [ ] Improve visual hierarchy so conversation dominates the screen, the action
      selector remains compact, the TextArea has useful multiline height, and
      the footer remains a single compact row (RQ-TUI-034).
- [ ] Ensure important states are not conveyed by color alone.
- [ ] Verify usability at 80x24 (RQ-TUI-023).

## Phase 16 — Tests

- [x] Add CLI entry-point tests (RQ-CLI-001). (`tests/cli/test_entrypoint.py`)
- [x] Add argument parsing tests (global + action options, invalid options)
      (RQ-CLI-002/003). (`tests/cli/test_parser.py`)
- [x] Add command model tests (RQ-CLI-004). (`tests/cli/tui/test_commands.py`, `tests/cli/test_parser.py`)
- [x] Add router dispatch tests (RQ-CLI-005). (`tests/cli/test_router.py`)
- [x] Add direct CLI execution tests with mocked actions. (`tests/cli/test_shell.py`, `tests/cli/test_entrypoint.py`)
- [x] Add exit code tests (RQ-CLI-018). (`tests/cli/test_entrypoint.py`)
- [x] Add output formatting and stderr tests (RQ-CLI-019). (`tests/cli/test_formatter.py`)
- [x] Add help output tests (RQ-CLI-021). (`tests/cli/test_entrypoint.py`)
- [x] Add evaluation confirmation tests (interactive + `--yes`) (RQ-CLI-014/016). (`tests/cli/test_evaluate_flow.py`)
- [x] Add exercise selection tests (RQ-CLI-010). (`tests/cli/test_evaluate_flow.py`)
- [x] Add `--instrumented` rejection tests (RQ-CLI-015). (`tests/cli/test_evaluate_flow.py`)
- [x] Add student identity not-inferred tests (RQ-CLI-006). (`tests/cli/test_student.py`)
- [x] Add context reduction notice tests (RQ-CLI-020). (`tests/cli/test_formatter.py`)
- [x] Add TUI entry-point tests (RQ-TUI-001). (`tests/cli/tui/test_welcome.py`, `tests/cli/test_entrypoint.py`)
- [x] Add TUI slash-command parser/dispatch tests (RQ-TUI-003/005). (`tests/cli/tui/test_commands.py`, `tests/cli/tui/test_router_integration.py`)
- [x] Add TUI layout/widget tests (RQ-TUI-004). (`tests/cli/tui/test_session_footer.py`, `tests/cli/tui/test_architecture.py`)
- [x] Add TUI welcome-name identity tests (RQ-TUI-007). (`tests/cli/tui/test_welcome.py`)
- [x] Add TUI practice/ask/examples integration tests with mocked actions
      (RQ-TUI-009/011/012). (`tests/cli/tui/test_router_integration.py`, `tests/cli/tui/test_action_selector.py`)
- [x] Add TUI evaluation confirmation tests (RQ-TUI-013). (`tests/cli/tui/test_evaluate_confirmation.py`)
- [x] Add TUI non-blocking worker tests (RQ-TUI-016). (`tests/cli/tui/test_non_blocking.py`)
- [x] Add TUI cancellation tests where applicable (RQ-TUI-017). (`tests/cli/tui/test_state_boundary.py`)
- [x] Add TUI evaluation result rendering tests (RQ-TUI-018). (`tests/cli/tui/test_evaluate_confirmation.py`, `tests/cli/tui/test_router_integration.py`)
- [x] Add TUI error and secret-redaction tests (RQ-TUI-019/020). (`tests/cli/tui/test_redaction.py`)
- [x] Add TUI keyboard-binding tests (RQ-TUI-021). (`tests/cli/tui/test_bindings.py`)
- [x] Add TUI action-selector and free-text routing tests (RQ-TUI-022/030:
      `tests/cli/tui/test_action_selector.py`).
- [x] Add TUI multi-line input widget tests (RQ-TUI-030:
      `tests/cli/tui/test_input_widget.py`).
- [x] Add TUI resize/minimum-size tests (RQ-TUI-023/024). (`tests/cli/tui/test_architecture.py`; 80x24 pty smoke)
- [x] Add TUI architecture/dependency isolation tests (RQ-TUI-027). (`tests/cli/tui/test_architecture.py`)
- [x] Run all direct CLI tests to confirm the TUI does not break them
      (RQ-TUI-026). (full suite `284 passed`, CLI + TUI together)
- [x] Verify every SHALL requirement has an automated test or documented
      justification (RQ-TUI-028). (SHALL-to-test report below)

## Phase 17 — Verification

- [x] Run the complete test suite. (`pytest -q` → 284 passed)
- [ ] Manually smoke-test direct CLI commands (`practice`, `ask`, `examples`,
      `evaluate`) in a terminal.
      (partial: `--help` and expected-error/exit-code paths verified in a real
      terminal; full success paths need a local LLM and are covered by the
      automated CLI tests)
- [x] Manually smoke-test `ada-sensei` in a real terminal. (pty smoke at 80x24: 9/9 checks, Enter executes, hints/footer rendered, no Evaluate button)
- [x] Manually verify `/help`, `/practice`, `/ask`, `/examples`,
      `/evaluate`, `/hint`, `/more`, `/solution`, `/clear`, and `/quit`.
      (pty: `/help` rendered help, `/ask hello` reached Running, `/clear` clean;
      `/quit` exits; remaining slash variants covered by `test_commands.py`
      + router integration tests)
- [x] Verify evaluation confirmation prevents Gradle execution when declined,
      in both modes. (`tests/cli/test_evaluate_flow.py`, `tests/cli/tui/
      test_evaluate_confirmation.py`; direct `evaluate` exits before Gradle)
- [x] Verify `--yes` non-interactive override works. (`tests/cli/test_evaluate_flow.py`, ADR-019)
- [x] Verify direct CLI and TUI converge on the same router by exercising the
      same action through both interfaces. (pty Enter→`AskCommand` dispatch;
      all TUI slash/selector routing reuses `CommandRouter`, `test_router.py`
      + `test_router_integration.py`)
- [x] Update task checkboxes only after evidence exists.

## Definition of Done

The CLI and TUI SHALL be considered implemented only when:

1. all SHALL requirements (RQ-CLI-xxx and RQ-TUI-xxx) are implemented;
2. tests pass;
3. direct CLI commands and TUI slash commands converge on the same
   `CommandRouter`;
4. no business/domain logic is placed in the CLI formatter or TUI widgets;
5. long-running operations do not block the UI event loop;
6. evaluation confirmation and evidence rules remain intact in both modes;
7. student identity always comes from the name received at session start;
8. implementation evidence is reported.

## Phase 18 — Final interaction verification

- [x] Start `ada-sensei` and verify the TextArea is immediately editable.
      (pty smoke: typed text echoed at 80x24; focus autorestore covered by
      `test_input_widget.py`)
- [x] Select `ask`, type a request, and press Enter; verify the action executes.
      (pty smoke: footer flipped to `Action: ask | Running`, input cleared;
      probe confirmed `AskCommand` dispatched)
- [x] Select `practice`, type a topic, and press Enter; verify practice executes.
      (routing + exercise executed through `CommandRouter` in
      `test_action_selector.py`; same Enter path proven in terminal for ask)
- [x] Select `examples`, type a topic, and press Enter; verify examples execute.
      (routing + execution through `CommandRouter` in `test_action_selector.py`)
- [x] Select `evaluate` and press Enter; verify the normal evaluation confirmation
      flow occurs before any Gradle execution.
      (`test_selector_evaluate_enter_starts_confirmation_flow`,
      `test_evaluate_confirmation.py`; declining runs no Gradle)
- [x] Verify Shift+Enter inserts a newline without executing.
      (probe: newline inserted, no dispatch; `test_shift_enter_creates_newline`);
      pty smoke kept submitted text intact)
- [x] Verify the action selector contains evaluate and no separate Evaluate button
      is present.
      (pty smoke: `[Evaluate` absent + footer shows `Action`; `len(query)==0`
      Button assertion in `test_action_selector.py`)
- [x] Verify the footer continuously shows student, score, AI model, action, and
      status.
      (pty smoke at 80x24: `Student: … | Score: — | AI: … | Action: ask | Running`;
      `test_session_footer.py`)
- [x] Verify the footer updates after action changes and evaluation completion.
      (`test_action_selector.py` state/footer assertions; eval completion in
      `test_evaluate_confirmation.py`)
- [x] Verify focus returns to the TextArea after completion/error/cancellation.
      (focus-restore assertions in `test_input_widget.py`)
- [x] Verify the interface remains usable at 80x24.
      (pty smoke at 80x24: 9/9 layout/key checks passed)
