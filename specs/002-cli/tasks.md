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
- [ ] Implement the visible, changeable action selector (Textual `Select`) with
      `ask`, `practice`, and `examples` (RQ-TUI-004/030).
- [ ] Implement the multi-line text area input widget (Textual `TextArea` or
      equivalent) supporting multiple lines, Enter for new line, Ctrl+Enter to
      submit, and scrolling (RQ-TUI-030).
- [ ] Route free text that does not start with `/` to the selected action;
      slash-prefixed input remains a slash command (RQ-TUI-030).
- [ ] Provide `evaluate` as a separate visible action that consumes no free text
      (RQ-TUI-030, RQ-TUI-013).
- [ ] Add concise status/help hints.
- [ ] Ensure important states are not conveyed by color alone.
- [ ] Verify usability at 80x24 (RQ-TUI-023).

## Phase 16 — Tests

- [ ] Add CLI entry-point tests (RQ-CLI-001).
- [ ] Add argument parsing tests (global + action options, invalid options)
      (RQ-CLI-002/003).
- [ ] Add command model tests (RQ-CLI-004).
- [ ] Add router dispatch tests (RQ-CLI-005).
- [ ] Add direct CLI execution tests with mocked actions.
- [ ] Add exit code tests (RQ-CLI-018).
- [ ] Add output formatting and stderr tests (RQ-CLI-019).
- [ ] Add help output tests (RQ-CLI-021).
- [ ] Add evaluation confirmation tests (interactive + `--yes`) (RQ-CLI-014/016).
- [ ] Add exercise selection tests (RQ-CLI-010).
- [ ] Add `--instrumented` rejection tests (RQ-CLI-015).
- [ ] Add student identity not-inferred tests (RQ-CLI-006).
- [ ] Add context reduction notice tests (RQ-CLI-020).
- [ ] Add TUI entry-point tests (RQ-TUI-001).
- [ ] Add TUI slash-command parser/dispatch tests (RQ-TUI-003/005).
- [ ] Add TUI layout/widget tests (RQ-TUI-004).
- [ ] Add TUI welcome-name identity tests (RQ-TUI-007).
- [ ] Add TUI practice/ask/examples integration tests with mocked actions
      (RQ-TUI-009/011/012).
- [ ] Add TUI evaluation confirmation tests (RQ-TUI-013).
- [ ] Add TUI non-blocking worker tests (RQ-TUI-016).
- [ ] Add TUI cancellation tests where applicable (RQ-TUI-017).
- [ ] Add TUI evaluation result rendering tests (RQ-TUI-018).
- [ ] Add TUI error and secret-redaction tests (RQ-TUI-019/020).
- [ ] Add TUI keyboard-binding tests (RQ-TUI-021).
- [ ] Add TUI action-selector and free-text routing tests (RQ-TUI-022/030:
      `tests/cli/tui/test_action_selector.py`).
- [ ] Add TUI multi-line input widget tests (RQ-TUI-030:
      `tests/cli/tui/test_input_widget.py`).
- [ ] Add TUI resize/minimum-size tests (RQ-TUI-023/024).
- [ ] Add TUI architecture/dependency isolation tests (RQ-TUI-027).
- [ ] Run all direct CLI tests to confirm the TUI does not break them
      (RQ-TUI-026).
- [ ] Verify every SHALL requirement has an automated test or documented
      justification (RQ-TUI-028).

## Phase 17 — Verification

- [ ] Run the complete test suite.
- [ ] Manually smoke-test direct CLI commands (`practice`, `ask`, `examples`,
      `evaluate`) in a terminal.
- [ ] Manually smoke-test `ada-sensei` in a real terminal.
- [ ] Manually verify `/help`, `/practice`, `/ask`, `/examples`,
      `/evaluate`, `/hint`, `/more`, `/solution`, `/clear`, and `/quit`.
- [ ] Verify evaluation confirmation prevents Gradle execution when declined,
      in both modes.
- [ ] Verify `--yes` non-interactive override works.
- [ ] Verify direct CLI and TUI converge on the same router by exercising the
      same action through both interfaces.
- [ ] Update task checkboxes only after evidence exists.

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
