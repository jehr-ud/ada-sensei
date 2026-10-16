# ADA Sensei — CLI and Interactive TUI Specification

## Objective

Provide ADA Sensei with a complete command-line interface (CLI) and an optional
interactive terminal user interface (TUI). The CLI owns argument parsing, command
routing, and application dispatch. The TUI is a presentation mode of the same
CLI layer. Both interfaces converge on the same Command Router and the same
Application Actions. Neither interface contains independent business logic.

## Scope

`002-cli` owns:

- argument parsing and validation;
- the command model (typed command objects);
- the command router (dispatch to application actions);
- direct non-interactive CLI execution;
- the interactive Textual-based TUI;
- progressive-assistance commands (`/hint`, `/more`, `/solution`);
- CLI/TUI error handling and output formatting;
- evaluation confirmation and non-interactive `--yes` behavior;
- integration with the application layer (practice, ask, examples, evaluate).

`002-cli` does NOT own:

- business logic for practice, ask, examples, or evaluation (003–006);
- domain models, persistence, LLM abstraction, or tooling (001-foundation);
- scoring, evaluation rubric, or evidence collection (006-evaluate).

## Direct CLI Experience

Running `ada-sensei` without a direct action starts the interactive TUI.
Running `ada-sensei <action> [args]` executes the action directly and exits.

```bash
ada-sensei practice --topic compose-state --difficulty intermediate
ada-sensei ask "Why does LazyColumn not update?"
ada-sensei examples ViewModel
ada-sensei evaluate --exercise exercise://<uuid> --yes
ada-sensei --help
ada-sensei practice --help
```

Student identity is the name provided at the start of an interactive session; no
`--student` option exists. Global options apply to all actions:

```text
--project <path>          active project/workspace path
--yes                     non-interactive Gradle execution confirmation
--offline                 disable network dependency resolution
```

Exit codes for direct commands:

- `0` — success
- `1` — expected user error (invalid input, student not found, action failed)
- `2` — unexpected internal failure

## Interactive TUI Experience

Running `ada-sensei` without arguments starts the Textual-based interactive TUI.

The TUI SHALL support slash commands:

```text
/help
/practice --topic compose-state --difficulty intermediate
/ask Why does LazyColumn not update?
/examples ViewModel
/evaluate --exercise exercise://<uuid>
/hint
/more
/solution
/name <name>  (update the student identity)
/clear
/quit
```

The TUI uses the same Command Router as direct CLI commands. Slash commands are
parsed into the same typed command objects that direct CLI argument parsing
produces.

Free text that does not start with `/` is submitted by pressing Enter and is
converted into a typed command according to the currently selected action.


## Design Principles

1. Both direct CLI and TUI converge on the same Command Router.
2. Business logic SHALL live in application actions, router, and foundation services.
3. Neither the CLI formatter nor the TUI widgets SHALL implement scoring, LLM
   prompting, persistence, Android analysis, or domain-state mutation.
4. The Command Router SHALL dispatch command objects to application actions.
5. Student identity SHALL always be explicit and SHALL never be inferred from
   prompt text, filesystem paths, environment variables, git configuration,
   usernames, project metadata, or OS user information.
6. Evaluation SHALL preserve the confirmation rules defined by this specification
   and `006-evaluate`.
7. Long-running TUI operations SHALL NOT block the Textual event loop.
8. The TUI SHALL use Textual widgets/layouts rather than custom ANSI/curses
   rendering where Textual provides an equivalent capability.
9. Only `ada_sensei/cli/tui/` SHALL import Textual-specific modules.

## Main Layout (TUI)

The TUI SHALL prioritize a simple conversational workflow:

1. Select the desired action.
2. Type the request in the persistent input area.
3. Press Enter to execute the selected action.
4. Use Shift+Enter when a new line is required.
5. Observe the result in the conversation area.

The primary action selector SHALL include all principal actions:

- `ask`
- `practice`
- `examples`
- `evaluate`
- `exam-init`
- `exam-finish`
- `learn`
- `diagnose`

`evaluate` is a normal selectable action. It SHALL NOT be represented as a separate
button outside the action selector.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ADA Sensei                                                                    │
│ Student: Jorge   Project: app   Exercise: compose-state                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Conversation / exercise / examples / evaluation output                     │
│                                                                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Action: [ ask ▼ ]                                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ Type your question, topic, request, or evaluation input...                   │
│                                                                              │
│                                                                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Student: Jorge | Score: 85 | AI: qwen2.5-coder:7b | Action: ask | Ready     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Enter Run  Shift+Enter New line  Ctrl+C Cancel  Ctrl+Q Quit  F2 Help         │
└──────────────────────────────────────────────────────────────────────────────┘
```

The input area SHALL remain an editable multiline Textual `TextArea`. The common
execution gesture SHALL be **Enter**.

- Enter SHALL submit the current input.
- Shift+Enter SHALL insert a new line.
- The input SHALL remain editable and focusable.
- The input SHALL regain focus after a command completes, fails, or is cancelled.
- The UI SHALL make the Enter-to-run behavior visible to the user.
- The selector SHALL remain independently changeable without clearing conversation
  output or the current input.
- `evaluate` SHALL be selected through the same action selector as the other
  principal actions.

This interaction is intentionally optimized for a conversational terminal:
**select action → type → Enter**.

## Technology

- Python 3.11+
- argparse or equivalent for direct CLI argument parsing
- Textual (TUI only)
- Rich (through Textual or directly for compatible rich content)

Only `ada_sensei/cli/tui/` SHALL import Textual-specific modules.

## Suggested Structure

```text
ada_sensei/
├── cli/
│   ├── __init__.py
│   ├── app.py              # CLI entry point, argument parsing, TUI launch
│   ├── commands.py         # typed command objects + CommandResult union
│   ├── router.py           # CommandRouter.dispatch()
│   ├── formatter.py        # plain-text output for direct CLI
│   └── tui/
│       ├── __init__.py
│       ├── app.py          # Textual App
│       ├── screens.py
│       ├── widgets.py
│       ├── messages.py
│       ├── state.py        # presentation state only
│       ├── bindings.py
│       └── styles.tcss
├── core/
├── actions/
├── llm/
├── tools/
├── android/
├── knowledge/
└── student/
```

The exact module names MAY differ if the architectural boundaries remain intact.

## Acceptance

The implementation is complete when:

1. direct CLI commands (`practice`, `ask`, `examples`, `evaluate`) work
   identically to their TUI slash-command counterparts;
2. both interfaces converge on the same Command Router;
3. the TUI starts from `ada-sensei` and supports all specified slash commands;
4. long-running TUI operations do not block the event loop;
5. student identity always comes from the name received at session start;
6. evaluation confirmation and evidence rules are intact in both modes;
7. automated tests cover all SHALL requirements;
8. no business/domain logic resides in the CLI formatter or TUI widgets.


## Onboarding and Student Intent

At first interactive launch, after student identity is established, the TUI SHALL
show: (a) ADA Sensei's goal, (b) the seven default Android stages from
`008-learning-path`, and (c) two choices: run an initial diagnostic or choose a
starting stage. It SHALL also explain the two intents: Study and Examine. The
student may skip the diagnostic and choose a stage explicitly.

The action selector SHALL expose `ask`, `practice`, `examples`, `evaluate`,
`exam-init`, `exam-finish`, `learn`, and `diagnose`. Existing actions remain
reusable and are not replaced by agent-specific commands.

The CLI/TUI SHALL dispatch all student intents through `TeacherAgent` via the
shared application router. The CLI and TUI remain presentation/routing layers and
SHALL NOT call Planner/Evaluator/Trainer directly. This applies to direct CLI
subcommands as well as slash commands and free-text requests.
