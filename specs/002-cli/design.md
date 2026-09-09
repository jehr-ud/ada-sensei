# ADA Sensei — CLI and TUI Design

## 1. Architecture

The CLI and the TUI are two presentation modes that converge on the same
Command Router and the same Application Actions.

```text
                    ┌──────────────┐
                    │ Direct CLI   │
                    └──────┬───────┘
                           │ user intent (argv)
                           ▼
                    ┌──────▼───────┐
                    │ Command      │
                    │ Parser       │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Command      │
                    │ Router       │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │ Application / Actions   │
              └────────────┬────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
   Practice              Ask              Evaluate
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                         Core
```

```text
                    ┌──────────────┐
                    │     TUI      │
                    │  cli/tui/*   │
                    └──────┬───────┘
                           │ slash command → same command objects
                           ▼
                    ┌──────▼───────┐
                    │ Command      │
                    │ Router       │
                    └──────────────┘
```

The Direct CLI parses `argv` into command objects and dispatches them through
the router. The TUI parses slash-command input into the same command objects and
dispatches them through the same router. The router is the single boundary
between presentation and application.

Only the `cli/tui/` package imports Textual. Core/domain services never depend
on Textual.

## 2. Command Model

The CLI SHALL represent each user intent as a typed command object:

```text
PracticeCommand(topic: str | None, difficulty: Difficulty | None,
                objective: str | None, adaptive: bool)
AskCommand(question: str)
ExamplesCommand(topic: str)
EvaluateCommand(exercise_id: str | None, yes: bool,
                instrumented: bool = False)
ProjectCommand(path: str | None)
HintCommand
MoreCommand
SolutionCommand
HelpCommand(scope: HelpScope)
ClearCommand
QuitCommand
```

Both the direct CLI parser and the TUI slash-command parser produce these same
objects. The router dispatches on the command type.

## 3. Router Interface

```text
CommandRouter
  .dispatch(command: Command, context: SessionContext)
      -> CommandResult
```

`CommandResult` is a discriminated union:

```text
CommandResult
  = PracticeResult
  | Answer
  | ExampleResult
  | EvaluationResult
  | AssistanceResult
  | HelpResult
  | ClearResult
  | ErrorResponse     # expected user error
  | InternalFailure    # unexpected failure (sanitized)
```

The router SHALL NOT contain action business logic. It only maps a command type
to the corresponding application action and marshals the result.

## 4. CLI Entry Point

`cli/app.py`:

- parse global options (`--project`, `--yes`, `--offline`);
- if no action subcommand is present, launch the TUI;
- otherwise identify the action subcommand (`practice`, `ask`, `examples`,
  `evaluate`);
- parse and validate action-specific options;
- build the command object;
- call `CommandRouter.dispatch(command, session_context)`;
- format the `CommandResult` via `cli/formatter.py`;
- print to stdout (success) or stderr (errors);
- return the appropriate exit code (RQ-CLI-018).

The CLI SHALL NOT perform action business logic; it builds command objects and
dispatches them.

## 5. Direct CLI Execution Flow

```text
argv
  ↓
global option parsing
  ↓
no action? ──→ launch TUI
  ↓
action subcommand + options
  ↓
validate (RQ-CLI-003)
  ↓
build command object (RQ-CLI-004)
  ↓
CommandRouter.dispatch() (RQ-CLI-005)
  ↓
format result (formatter)
  ↓
stdout / stderr + exit code
```

Direct commands remain scriptable and deterministic (RQ-CLI-019, RQ-CLI-018).

## 6. Output Formatter

`cli/formatter.py` renders `CommandResult` to plain text for direct CLI output:

- exercises, answers, examples, and evaluation results;
- progress/status where applicable;
- error messages;
- exit codes.

The formatter SHALL redact secrets before display (RQ-CLI-019).

## 7. Error Handling

Expected user errors (invalid input, unknown student, action declined) produce
a clear message and exit code `1`. Unexpected failures are sanitized and exit
with code `2`; secrets are never exposed.

```text
✗ No student identity: provide your name at the start of the session.
```

```text
✗ The operation could not be completed.
  Check the local log for details.
```

## 8. Confirmation Flow (Evaluation)

Evaluation confirmation applies in both modes. In the direct CLI, an interactive
prompt is shown; in a non-interactive environment, Gradle execution is blocked
unless `--yes` is supplied (RQ-CLI-014, RQ-CLI-016, ADR-019).

```text
/evaluate  or  ada-sensei evaluate
   │
   ▼
Show evaluation scope
   │
   ▼
Confirm Gradle execution?
   │
 ┌─┴─────────────┐
No               Yes
 │                 │
Abort              ▼
                 EvaluateAction
                    ├─ inspect
                    ├─ build/compile
                    ├─ unit tests
                    ├─ Android Lint
                    └─ Detekt
                    ▼
               EvaluationResult
```

`connectedAndroidTest` SHALL not be launched (RQ-CLI-015).

## 9. Student Selection

```text
TUI welcome: "What is your name?" (name becomes student_id)
   │
   ▼
student exists? → set student_id (session)
   │
   └─ missing → create locally from the received name (RQ-FND-024)
```

Student identity is never inferred from prompt text, files, environment, or OS
user information (RQ-CLI-006, ADR-015).

## 10. Session Context

Both modes share the existing `SessionContext`. The TUI may display
`student_id`, project path, `exercise_id`, and assistance state when exposed.
Neither mode owns authoritative session state.

The TUI state module contains presentation state only (current screen, visible
messages, input contents, loading state) (RQ-TUI-025).

## 11. Long-running Work (TUI)

Use Textual's worker/async mechanisms (or an application-provided async bridge)
so LLM and evaluation operations do not block rendering/input handling.

```text
TUI event
   ▼
start worker
   ├── UI remains responsive
   ▼
application action (via router)
   ▼
result/status event
   ▼
update widgets
```

Do not call blocking subprocesses, Gradle, or synchronous network/model
operations directly from a widget event handler (RQ-TUI-016).

## 12. Context Reduction Notice

When the `ContextManager` reports reduction or summarization (RQ-FND-028), the
CLI formatter and TUI render the notice to the user (RQ-CLI-020). Neither mode
implements its own context-management strategy.

## 13. TUI Application

`cli/tui/app.py`:

- create the Textual `App`;
- install global bindings;
- mount the main screen;
- expose presentation state;
- present the action selector and map free text to the selected action
  (RQ-TUI-030);
- parse slash commands into command objects;
- dispatch via `CommandRouter` to the application/router layer;
- display returned results and status events.

It SHALL NOT contain domain algorithms.

## 14. Screens and Widgets (TUI)

```text
TuiApp
  ├── HeaderWidget
  ├── ConversationView
  │    ├── UserMessage
  │    ├── AssistantMessage
  │    ├── ExerciseMessage
  │    ├── HintMessage
  │    ├── ExampleMessage
  │    ├── EvaluationMessage
  │    └── ErrorMessage
  ├── ActionSelector        (Select: ask | practice | examples)
  ├── EvaluateButton        (separate action, no free text)
  ├── InputWidget           (multi-line text area, persistent)
  └── StatusBar
```

The visible, changeable action selector (Textual `Select`) is the discoverable
action selection mechanism (RQ-TUI-022, RQ-TUI-030). Free text that does not
start with `/` is sent to the selected action; slash-prefixed text is parsed as
a slash command.

The `InputWidget` SHALL be a multi-line text area (Textual `TextArea` or
equivalent) supporting:
- Multiple lines of input (Enter adds a new line)
- Ctrl+Enter (or configured keybinding) to submit
- Horizontal and vertical scrolling for long content
- Placeholder text indicating the current action context

## 15. Evaluation Progress Events (TUI)

Evaluation progress SHOULD be represented by events defined in the application
interface (not inside the TUI):

```text
INSPECTION_STARTED
BUILD_STARTED
BUILD_COMPLETED
UNIT_TESTS_STARTED
UNIT_TESTS_COMPLETED
LINT_STARTED
LINT_COMPLETED
DETEKT_STARTED
DETEKT_COMPLETED
EVALUATION_COMPLETED
```

## 16. Rendering (TUI)

Use Textual/Rich rendering primitives for:

- Markdown-like text;
- syntax-highlighted code;
- tables;
- status indicators;
- progress indicators;
- validation/error messages.

Avoid custom ANSI escape sequences when a Textual/Rich equivalent exists.

## 17. Theme and Accessibility (TUI)

The initial theme SHALL prioritize readability and terminal compatibility. The
implementation SHOULD:

- avoid relying only on color to convey meaning;
- use textual labels/icons in addition to colors;
- preserve readable contrast;
- support terminal resizing;
- avoid excessive animation.

## 18. Dependency Isolation

Only the following package is allowed to import Textual:

```text
ada_sensei.cli.tui
```

A CI architecture test SHOULD fail if `core`, `actions`, `llm`, `student`, or
`android` import Textual (RQ-TUI-027).

## 20. Welcome Greeting (TUI, RQ-TUI-029)

On mount, the TUI prompts for the student's name; the received name IS the
student identity:

```text
TUI mount
   ▼
prompt "What is your name?" (always, when no session identity is restored)
   ▼
HistoryStore.has(name)?
   ├── no ► create_profile(name, confirmed=True); set_name(name)
   │         "Welcome, <name>!"
   └── yes ► "Welcome back, <name>!"
   ▼
SessionContext.set_student(name)
```

- The name provided by the student at the welcome greeting is used as
  `student_id` (`RQ-CLI-006`, `RQ-TUI-007`, ADR-015).
- The name is persisted to the student's `StudentProfile`.
- The name SHALL NOT be inferred from input; identity always comes from the
  name the user provides at the welcome greeting.

## 21. Testing Strategy

### CLI tests

1. argument parsing (global + action options);
2. command model construction;
3. router dispatch;
4. direct CLI execution (end-to-end, mocked actions);
5. exit codes;
6. output formatting (stdout/stderr, redaction);
7. help output;
8. confirmation flow (interactive and `--yes`);
9. exercise selection (`--exercise` + session fallback);
10. `--instrumented` rejection;
11. context reduction notice.

### TUI tests

1. command parsing;
2. screen/widget composition;
3. slash command dispatch (to same router);
4. welcome-name identity binding;
5. action delegation;
6. evaluation confirmation;
7. worker/non-blocking behavior;
8. error and secret redaction;
9. keyboard bindings;
10. terminal resizing/minimum size;
11. direct CLI regression tests;
12. architecture/dependency isolation.
