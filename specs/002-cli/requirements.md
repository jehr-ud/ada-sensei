# Requirements

## CLI / Application Interface Requirements

## RQ-CLI-001 Entry point

When `ada-sensei` is executed without a direct action subcommand, the system
SHALL start the Textual-based interactive TUI. When `ada-sensei <action>` is
executed, the system SHALL run the action directly and exit.

## RQ-CLI-002 Global options

The CLI SHALL accept the global options `--project <path>`, `--yes`, and
`--offline`, applying to all actions.

## RQ-CLI-003 Action parsing

The CLI SHALL parse and validate action-specific options (`--topic`,
`--difficulty`, `--objective`, `--adaptive`/`--no-adaptive`, `--exercise`,
`--instrumented`, question text, topic text) before dispatch. Invalid or
missing required options SHALL produce a clear error without executing the
action.

## RQ-CLI-004 Command model

The CLI SHALL represent each user intent as a typed command object (for example
`PracticeCommand`, `AskCommand`, `ExamplesCommand`, `EvaluateCommand`,
`ProjectCommand`, `HintCommand`, `MoreCommand`, `SolutionCommand`). Both direct
CLI input and TUI slash-command input SHALL produce the same command objects.

## RQ-CLI-005 Command routing

The CLI SHALL dispatch command objects to the corresponding application action
through a single `CommandRouter`. The router SHALL NOT contain action business
logic.

## RQ-CLI-006 Student identity

Student identity SHALL be established only from the name provided by the student
at the start of an interactive session (the TUI welcome greeting). The CLI and
TUI SHALL NOT accept a student identity through any option or command, and SHALL
NOT infer student identity from filesystem paths, environment variables, git
configuration, usernames, project metadata, OS user information, or prompt
content. If the student record does not exist, the CLI SHALL follow `RQ-FND-024`
and create it from the received name.

## RQ-CLI-007 Project selection

The CLI SHALL accept the active project/workspace path through `--project
<path>` and SHALL expose it to the application layer as the active project. The
TUI SHALL display the active project when known.

## RQ-CLI-010 Exercise selection

The CLI SHALL accept an explicit `--exercise exercise://<uuid>` option to
select the exercise for evaluation. When omitted, the session's current
exercise (`SessionContext.current_exercise_id`) SHALL be used. When no exercise
is available, only structural (non-requirement) dimensions SHALL be evaluated.

## RQ-CLI-014 Evaluation confirmation

Before executing any Gradle-based evaluation task, the CLI SHALL request
explicit user confirmation (an interactive prompt in the terminal, or a
confirmation dialog in the TUI). Declining confirmation SHALL abort the
evaluation cleanly without starting any Gradle process. Project inspection alone
does not require confirmation.

## RQ-CLI-015 Instrumented tests

The default evaluation SHALL NOT run `connectedAndroidTest`. The `--instrumented`
option is reserved for future use; if supplied today, the CLI SHALL report it as
unsupported and SHALL NOT launch instrumented tests.

## RQ-CLI-016 Non-interactive evaluation

In a non-interactive execution environment, `evaluate` SHALL abort before
Gradle-based execution unless the explicit `--yes` confirmation override is
supplied.

## RQ-CLI-017 Progressive assistance

The CLI SHALL expose `/hint`, `/more`, and `/solution` commands (in the TUI) and
equivalent mechanisms (in the direct CLI, when applicable) that delegate
assistance progression to the session/action layer. The CLI SHALL NOT
independently calculate the assistance level.

## RQ-CLI-018 Exit codes

Direct CLI commands SHALL return exit code `0` on success, `1` on expected user
error, and `2` on unexpected internal failure.

## RQ-CLI-019 Output and errors

Direct CLI commands SHALL write human-readable plain text output to stdout and
errors to stderr. Secrets and sensitive configuration values SHALL NOT be
displayed in output or errors.

## RQ-CLI-020 Context reduction notice

When the `ContextManager` reduces or summarizes context, the CLI and TUI SHALL
display a notice to the user (RQ-FND-028).

## RQ-CLI-021 Help

`ada-sensei --help` SHALL list available actions, global options, a brief
description of each, and a concrete usage example. `ada-sensei <action> --help`
SHALL list the action-specific options.

---

## Interactive TUI Requirements

## RQ-TUI-001 TUI entry

When `ada-sensei` is executed without a direct action, the system SHALL start
the Textual-based interactive TUI.

## RQ-TUI-002 Presentation-layer boundary

The TUI SHALL only coordinate presentation and user interaction. It SHALL NOT
contain business logic for practice, ask, examples, evaluation, scoring,
persistence, LLM prompting, or Android project analysis.

## RQ-TUI-003 Shared command routing

TUI slash commands SHALL be parsed into the same typed command objects and
dispatched through the same `CommandRouter` used by direct CLI commands. The
TUI SHALL NOT implement duplicate versions of actions.

## RQ-TUI-004 Main layout

The TUI SHALL provide:

- a header showing ADA Sensei and relevant session context;
- a scrollable main output/conversation area;
- a persistent text input area;
- a visible, changeable action selector (RQ-TUI-030);
- a status/help area.

## RQ-TUI-005 Slash commands

The TUI SHALL recognize at least:

`/help`, `/practice`, `/ask`, `/examples`, `/evaluate`, `/hint`, `/more`,
`/solution`, `/clear`, and `/quit`.

Unknown slash commands SHALL produce a clear user-facing error without
terminating the TUI.

## RQ-TUI-006 Help

`/help` SHALL display the available slash commands, a concise description of
their purpose, and a concrete usage example for each command.

## RQ-TUI-007 Student identity

The student identity SHALL be the name the student provides at the TUI welcome
greeting (RQ-TUI-029). The TUI SHALL never infer student identity from
questions, files, environment variables, or conversational content.

No `/student` command exists; identity is established by the received name. If
the student does not exist, the TUI SHALL create it from the received name,
following `RQ-FND-024` and `RQ-CLI-006`.

## RQ-TUI-008 Project context

The TUI SHALL display the active project when known and SHALL provide a path or
command flow for selecting/configuring the active project.

## RQ-TUI-009 Practice integration

`/practice` SHALL pass supported practice options to the practice action,
including topic, difficulty, objective, and adaptive mode.

The TUI SHALL render the resulting exercise without recalculating or changing
its pedagogical content.

## RQ-TUI-010 Progressive assistance

`/hint`, `/more`, and `/solution` SHALL delegate assistance progression to the
existing session/action layer via the `CommandRouter`. The TUI SHALL not
independently calculate the assistance level.

The TUI SHALL visually distinguish progressive assistance from ordinary
answers where the underlying result provides that information.

## RQ-TUI-011 Ask integration

`/ask <question>` SHALL submit the question through the existing ask action.
The TUI SHALL display the response and preserve the presentation-level
conversation context required for continued interaction.

## RQ-TUI-012 Examples integration

`/examples <topic>` SHALL invoke the examples action and SHALL display returned
examples with readable formatting and syntax highlighting where available.

Incorrect examples SHALL be clearly labeled when the action marks them as such.

## RQ-TUI-013 Evaluation confirmation

Before any Gradle-based evaluation task is executed, the TUI SHALL request an
explicit confirmation from the user.

Declining confirmation SHALL abort the execution cleanly without starting the
Gradle task.

## RQ-TUI-014 Non-interactive evaluation

The direct non-interactive `evaluate` command SHALL preserve the existing
`--yes` requirement. The TUI SHALL not weaken or bypass this policy.

## RQ-TUI-015 Evaluation progress

While evaluation is running, the TUI SHALL show a meaningful progress/status
state for long-running stages such as inspection, build/compile, tests, Lint,
and Detekt when those stages are executed.

The TUI SHALL display progress received from the evaluation/application layer;
it SHALL not fabricate progress or evidence.

## RQ-TUI-016 Non-blocking operations

Long-running operations, including evaluation and LLM requests, SHALL execute
without blocking the Textual UI event loop.

The user SHALL be able to observe application status while the operation runs.

## RQ-TUI-017 Cancellation

The TUI SHOULD provide a user-accessible cancellation mechanism for operations
that support cancellation. Cancellation SHALL be propagated to the application
layer rather than implemented by forcibly mutating domain state in a widget.

## RQ-TUI-018 Evaluation result rendering

The TUI SHALL render `EvaluationResult` data returned by the evaluation layer,
including score, rubric dimensions, evidence, limitations, and actionable
feedback when present.

The TUI SHALL never calculate or alter the official evaluation score.

## RQ-TUI-019 Error handling

Expected user errors SHALL be rendered as clear messages without stack traces.
Unexpected failures SHALL be sanitized and SHALL not expose secrets or
sensitive configuration values.

The TUI SHOULD provide a useful recovery hint when possible.

## RQ-TUI-020 Secret redaction

The TUI SHALL NOT display API credentials, tokens, passwords, or other secret
configuration values in normal output, diagnostics, or error messages.

## RQ-TUI-021 Keyboard interaction

The TUI SHALL support at least:

- Enter to submit the current input;
- Ctrl+C or an equivalent safe cancellation behavior;
- Ctrl+D or `/quit` to exit the application cleanly;
- scrolling of the main output area.

## RQ-TUI-022 Command palette

The TUI SHALL expose a discoverable action selection mechanism for the
principal actions. The visible action selector (RQ-TUI-030) satisfies this
requirement.

## RQ-TUI-023 Minimum terminal size

The TUI SHALL remain usable at a terminal size of at least 80 columns by 24
rows. It SHALL degrade gracefully when the terminal is smaller.

## RQ-TUI-024 Responsive rendering

The layout SHALL adapt to terminal resizing without losing domain state or
silently discarding user input.

## RQ-TUI-025 Presentation state

Presentation-only state MAY include current screen, visible messages,
input contents, and loading state. Authoritative domain state SHALL remain in
foundation/application services.

## RQ-TUI-026 Direct CLI compatibility

Adding the TUI SHALL NOT break direct commands such as `practice`, `ask`,
`examples`, and `evaluate`.

## RQ-TUI-027 Dependency isolation

Textual-specific imports SHALL be confined to the TUI package. Core/domain,
action, LLM, persistence, and Android analysis packages SHALL remain independent
of Textual.

## RQ-TUI-028 Testing

Every SHALL requirement in this specification SHALL have an automated test or
a documented reason why automated testing is not applicable.

## RQ-TUI-029 Welcome greeting with name

On startup, the TUI SHALL ask the user for their name before proceeding and
SHALL use that name as the current student identity (`student_id`). The TUI
SHALL persist the name to the student's `StudentProfile` so the profile records
the identity.

When a profile for the received name already exists, the welcome message SHALL
greet the user by that name (`Welcome back, <name>!`). The display name SHALL
NOT be inferred from any context; identity always comes from the name the user
provides at the welcome greeting (RQ-CLI-006, RQ-TUI-007).

## RQ-TUI-030 Action selector and free-text input

The TUI SHALL present a persistent, visible action selector for the principal
actions: `ask`, `practice`, and `examples`. The selector SHALL be changeable at
any time without leaving the conversation view.

The text input area SHALL remain always present and SHALL be a multi-line text
area (not a single-line input) to support writing longer questions, code
snippets, or detailed requests. The user SHALL be able to press Enter to add
new lines and Ctrl+Enter (or a configurable keybinding) to submit the content.

When the submitted text starts with `/`, it SHALL be parsed as a slash command
(RQ-TUI-005). Otherwise the submitted text SHALL be sent to the currently
selected action:

- `ask`: the free text becomes the question;
- `practice`: the free text becomes the topic (may be empty);
- `examples`: the free text becomes the topic.

`evaluate` SHALL be available as a separate, visible action that does not
consume free text (RQ-TUI-013).

The action selector and free-text routing SHALL build the same typed command
objects used by the CLI and dispatched through the shared `CommandRouter`
(RQ-TUI-003).

---

## Traceability

### CLI / Application Interface

| Requirement | Primary component | Test |
|---|---|---|
| RQ-CLI-001 | `cli/app.py` | `tests/cli/test_entry.py::test_tui_entry` / `test_direct_action` |
| RQ-CLI-002 | `cli/app.py` | `tests/cli/test_args.py::test_global_options` |
| RQ-CLI-003 | `cli/app.py` | `tests/cli/test_args.py::test_action_options` / `test_invalid_options` |
| RQ-CLI-004 | `cli/commands.py` | `tests/cli/test_commands.py::test_command_model` |
| RQ-CLI-005 | `cli/router.py` | `tests/cli/test_router.py::test_dispatch` |
| RQ-CLI-006 | `cli/tui/app.py`, `SessionContext` | `tests/cli/test_student.py::test_identity_never_inferred` |
| RQ-CLI-007 | `cli/app.py`, `SessionContext` | `tests/cli/test_project.py::test_project_selection` |
| RQ-CLI-010 | `EvaluateCommand` + action | `tests/cli/test_exercise.py::test_exercise_selection` |
| RQ-CLI-014 | `cli/app.py`, `EvaluateAction` | `tests/cli/test_evaluate_flow.py::test_confirmation_required` |
| RQ-CLI-016 | `cli/app.py`, `EvaluateAction` | `tests/cli/test_evaluate_flow.py::test_non_interactive_aborts_without_yes` |
| RQ-CLI-015 | `cli/app.py`, `EvaluateAction` | `tests/cli/test_evaluate_flow.py::test_instrumented_rejected` |
| RQ-CLI-017 | `router` + session/action | `tests/cli/test_assistance.py::test_progression_delegated` |
| RQ-CLI-018 | `cli/app.py` | `tests/cli/test_exit_codes.py::test_exit_codes` |
| RQ-CLI-019 | `cli/formatter.py` | `tests/cli/test_formatter.py::test_stdout_stderr` / `test_redaction` |
| RQ-CLI-020 | formatter / TUI status | `tests/cli/test_context_notice.py::test_notice_displayed` |
| RQ-CLI-021 | `cli/app.py` | `tests/cli/test_help.py::test_help_output` |

### TUI

| Requirement | Primary component | Test |
|---|---|---|
| RQ-TUI-001 | `cli/tui/app.py` | `tests/cli/tui/test_app.py::test_tui_entry` |
| RQ-TUI-002 | TUI package boundary | `tests/cli/tui/test_architecture.py` |
| RQ-TUI-003 | `CommandRouter` bridge | `tests/cli/tui/test_router_integration.py` |
| RQ-TUI-004 | screens/widgets | `tests/cli/tui/test_layout.py` |
| RQ-TUI-005 | command parser | `tests/cli/tui/test_commands.py` |
| RQ-TUI-006 | help widget/command | `tests/cli/tui/test_commands.py::test_help` |
| RQ-TUI-007 | welcome/name flow, `SessionContext` | `tests/cli/tui/test_welcome.py` |
| RQ-TUI-008 | project context | `tests/cli/tui/test_project.py` |
| RQ-TUI-009 | practice bridge | `tests/cli/tui/test_practice.py` |
| RQ-TUI-010 | assistance bridge | `tests/cli/tui/test_assistance.py` |
| RQ-TUI-011 | ask bridge | `tests/cli/tui/test_ask.py` |
| RQ-TUI-012 | examples bridge | `tests/cli/tui/test_examples.py` |
| RQ-TUI-013 | evaluate flow | `tests/cli/tui/test_evaluate_confirmation.py` |
| RQ-TUI-014 | CLI compatibility | `tests/cli/test_evaluate_flow.py` |
| RQ-TUI-015 | progress rendering | `tests/cli/tui/test_progress.py` |
| RQ-TUI-016 | workers/async bridge | `tests/cli/tui/test_non_blocking.py` |
| RQ-TUI-017 | cancellation | `tests/cli/tui/test_cancellation.py` |
| RQ-TUI-018 | result renderer | `tests/cli/tui/test_evaluation_result.py` |
| RQ-TUI-019 | error renderer | `tests/cli/tui/test_errors.py` |
| RQ-TUI-020 | formatter | `tests/cli/tui/test_redaction.py` |
| RQ-TUI-021 | bindings | `tests/cli/tui/test_bindings.py` |
| RQ-TUI-022 | action selector | `tests/cli/tui/test_action_selector.py` |
| RQ-TUI-023 | responsive layout | `tests/cli/tui/test_small_terminal.py` |
| RQ-TUI-024 | responsive layout | `tests/cli/tui/test_resize.py` |
| RQ-TUI-025 | presentation state | `tests/cli/tui/test_state_boundary.py` |
| RQ-TUI-026 | CLI entry/parser | `tests/cli/test_direct_commands.py` |
| RQ-TUI-027 | package architecture | `tests/cli/tui/test_architecture.py` |
| RQ-TUI-028 | test suite | CI/test coverage verification |
| RQ-TUI-029 | `cli/tui/app.py`, `StudentProfile` | `tests/cli/tui/test_welcome.py` |
| RQ-TUI-030 | action selector + input routing | `tests/cli/tui/test_action_selector.py` |
| RQ-TUI-030 | multi-line input widget | `tests/cli/tui/test_input_widget.py` |
