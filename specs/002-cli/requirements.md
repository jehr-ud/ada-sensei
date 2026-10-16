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

- a compact header showing ADA Sensei and relevant session context;
- a scrollable main output/conversation area;
- a persistent editable text input area;
- a visible, changeable action selector;
- a persistent footer/status area showing session and operation information;
- concise keyboard/help guidance.

The main action selector SHALL include `ask`, `practice`, `examples`, and `evaluate`.
`evaluate` SHALL NOT require a separate Evaluate button.

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

- Enter to execute the currently selected action;
- Shift+Enter to insert a new line in the text area;
- Ctrl+C or an equivalent safe cancellation behavior;
- Ctrl+D or `/quit` to exit the application cleanly;
- scrolling of the main output area.

The Enter-to-run behavior SHALL be discoverable from the visible UI.

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

On the first run, the TUI SHALL ask the user for their name before proceeding
and SHALL use that name as the current student identity (`student_id`). The TUI
SHALL persist the received name to the student's `StudentProfile` and also SHALL
save it as the last used student name in the data directory.

On subsequent runs, when a last used student name exists, the TUI SHALL start
directly with that identity and SHALL NOT ask for the name again. The user MAY
update their identity at any time with the `/name <name>` command; an updated
name SHALL become the current identity and SHALL replace the remembered one.

When a profile for the received name already exists, the welcome message SHALL
greet the user by that name (`Welcome back, <name>!`). The display name SHALL
NOT be inferred from any context; identity always comes from a name the user
provides (RQ-CLI-006, RQ-TUI-007).

## RQ-TUI-030 Action selector and free-text execution

The TUI SHALL present a persistent, visible action selector containing:

- `ask`
- `practice`
- `examples`
- `evaluate`

The selector SHALL be changeable at any time without leaving the conversation
view.

The text input area SHALL remain always present and SHALL be an editable
multi-line `TextArea`. The common execution gesture SHALL be **Enter**.

- Enter SHALL execute the currently selected action.
- Shift+Enter SHALL insert a new line.
- The text area SHALL remain editable and focusable.
- The TUI SHALL restore focus to the text area after command completion, error,
  or cancellation.
- The UI SHALL visibly communicate that Enter executes the selected action.

When the submitted text starts with `/`, it SHALL be parsed as a slash command
(RQ-TUI-005). Otherwise the submitted text SHALL be sent to the currently
selected action:

- `ask`: the free text becomes the question;
- `practice`: the free text becomes the topic (may be empty);
- `examples`: the free text becomes the topic;
- `evaluate`: the command SHALL use the normal evaluation flow and confirmation
  policy; free text SHALL NOT bypass the typed command contract.

`evaluate` SHALL use the same selector as the other principal actions. It SHALL
NOT be represented by a separate Evaluate button.

The action selector and free-text routing SHALL build the same typed command
objects used by the CLI and dispatched through the shared `CommandRouter`
(RQ-TUI-003).


---


## RQ-TUI-031 Input focus and execution

The TUI SHALL keep the text input editable whenever the application is in a state
that accepts user input. On initial readiness and after a command finishes, fails,
or is cancelled, the TUI SHALL return focus to the text input unless the user is
actively interacting with another control.

Normal text entry SHALL NOT be consumed by global application bindings.

## RQ-TUI-032 Persistent session footer

The TUI SHALL display a persistent footer/status area containing, when available:

- current student name;
- latest authoritative evaluation score;
- currently configured AI model;
- current selected action;
- current operation status.

Unavailable values SHALL be displayed explicitly (for example, `Score: —`) rather
than inferred or fabricated.

The TUI SHALL NOT calculate scores or select the AI model. It SHALL render values
provided by the application/session/LLM configuration layers.

## RQ-TUI-033 Action selector completeness

The visible action selector SHALL be the primary mechanism for choosing the current
principal action. It SHALL include `ask`, `practice`, `examples`, and `evaluate`.

Changing the selector SHALL immediately update presentation state, input
placeholder, footer action value, and subsequent free-text routing.

The selector SHALL not clear existing conversation output.

## RQ-TUI-034 Conversational visual hierarchy

The TUI SHALL visually prioritize:

1. conversation/output;
2. current action selector;
3. text input;
4. persistent session footer;
5. concise keyboard guidance.

The interface SHALL avoid presenting a separate Evaluate button when `evaluate` is
already available in the action selector.

The input area SHALL have sufficient visible height for multiline text while
remaining subordinate to the conversation area.

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
| RQ-TUI-039 | input history navigation | `tests/cli/tui/test_input_history.py` |
| RQ-TUI-035 | action registry + selector | `tests/cli/test_action_registry.py`, `tests/cli/tui/test_gui_selector.py` |
| RQ-TUI-036 | learning stage header | `tests/learning/test_stage_status.py`, `tests/cli/tui/test_gui_selector.py` |
| RQ-TUI-037 | version display | `tests/runtime/test_version.py` |
| RQ-TUI-038 | bilingual selector/status | `tests/locale/test_ui_strings.py`, `tests/cli/tui/test_gui_selector.py` |


## Learning Onboarding and Intent

### RQ-CLI-030 First-run welcome
On first interactive launch for a student without a learning profile, the TUI
SHALL display ADA Sensei's learning goal, all configured stages from the
validated catalog in catalog order, and
choices to run a diagnostic or select a starting stage.

### RQ-CLI-031 Study and Examine intents
The interface SHALL distinguish Study intent from Examine intent. Study supports
learning, practice, and mastery progression; Examine uses `/exam-init` and
`/exam-finish` and may be started at any learning stage.

### RQ-CLI-032 Reusable action selector
The action selector SHALL include ask, practice, examples, evaluate, exam-init,
exam-finish, learn, diagnose, language, and help, dispatching through the
shared router. Language changes SHALL NOT reset progress; help SHALL render the
shared help text.

### RQ-CLI-033 Teacher entry point
All student-facing actions SHALL be dispatched through TeacherAgent; the CLI/TUI
SHALL NOT orchestrate specialist agents itself.

## RQ-TUI-035 Graphical action selector completeness and routing

The TUI action selector SHALL expose every registered student-facing action
from the centralized registry (`cli/action_registry.py`): ask, practice,
examples, evaluate, exam-init, exam-finish, learn, diagnose, language, help.
Each definition SHALL carry a stable id, Spanish/English names, descriptions,
input hints, and the typed-command factory. The selector SHALL:

- display the localized label for the active locale (`es-CO`/`en-US`);
- route each selection to its existing workflow via the shared
  `CommandRouter` (Practice→Planner/Trainer, Ask→teaching workflow,
  Examples→example generation, Evaluate→evidence+evaluation engine,
  Learn→planning workflow, Language→persisted locale, Exam→exam workflow);
- keep CLI commands and TUI slash commands working through the same registry;
- register no action twice;
- block duplicate submissions while an action is running (busy guard) while
  keeping cancellation available;
- keep unavailable actions discoverable with an explicit prerequisite
  explanation (e.g. evaluate without an active project, exam-finish without an
  active exam) instead of silently hiding them;
- show loading, success, and error states consistently without placing
  business logic in UI components.

## RQ-TUI-036 Current learning stage header

The main interface SHALL persistently display the student's actual current
learning stage, resolved read-only from the persisted `LearningProfile` and
the locale-specific stage catalog (`learning/status.py`), as
`Etapa actual: <n> — <nombre>` / `Current stage: <n> — <name>`, plus the
stage objective where space permits. The display SHALL:

- load at startup and refresh after learning/evaluation workflows and after a
  persisted progression decision;
- follow the selected locale for the stage name;
- show `Ruta de aprendizaje no iniciada` / `Learning path not started` when no
  profile exists, and a safe unavailable message for invalid stage references
  or configuration errors;
- never advance the stage on refresh and never infer mastery from activity
  counts;
- not display a new stage for a pending (unpersisted) evaluation.

## RQ-TUI-037 Application version display

The main interface SHALL persistently but unobtrusively display the installed
ADA Sensei application version (header preferred), sourced from the single
authoritative source (`ada_sensei/version.py`: installed package metadata with
`__version__` fallback matching `pyproject.toml`). Version retrieval SHALL NOT
require an LLM request; missing metadata SHALL degrade gracefully without
crashing; the application version SHALL NOT be confused with catalog/schema
versions.

## RQ-TUI-038 Bilingual selector and status header

Action names, descriptions, hints, selector help, stage status, progression
status, loading/error/empty states, and accessibility labels SHALL be localized
in `es-CO` and `en-US` (`locale/ui_strings.py` + registry labels, deterministic
`en-US` fallback). Switching locale SHALL refresh all selector and status
labels without resetting progress, attempts, or evaluation history. Stable
action ids, stage ids, and version values SHALL remain language-independent.

## RQ-TUI-039 Input prompt history navigation

The TUI SHALL keep a bounded history of non-empty user-submitted inputs for the current session. Pressing Up when the input caret is at the first line SHALL recall the previous submitted input without executing it. Repeated Up navigates to older entries; Down navigates to newer entries. Moving Down beyond the newest entry SHALL restore the unsent draft captured when history browsing began. Recalled prompts SHALL remain editable and SHALL execute only after explicit Enter submission.

Up/Down SHALL preserve normal multiline cursor movement when history navigation is inactive and the caret is not at the relevant boundary (Up at first line; Down at last line). Empty submissions and assistant/system messages SHALL NOT enter history. History navigation SHALL NOT mutate learning or exam domain state.

Automated tests SHALL cover navigation order, draft restoration, edit-before-submit, multiline cursor behavior, empty submissions, bounded history, and interaction with Enter/Shift+Enter and the selected action.
