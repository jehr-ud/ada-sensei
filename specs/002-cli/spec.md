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
/clear
/quit
```

The TUI uses the same Command Router as direct CLI commands. Slash commands are
parsed into the same typed command objects that direct CLI argument parsing
produces.

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

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ADA Sensei   Student: alice   Project: app   Exercise: compose-state        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Conversation / exercise / evaluation output                                │
│                                                                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌────────────────────────────────────────────────────────┐  │
│ │ Action: ▼   │ │                                                          │  │
│ │ ask ▼       │ │  Type your question, topic, or request here...         │  │
│ │ practice    │ │  (supports multiple lines, press Ctrl+Enter to send)   │  │
│ │ examples    │ │                                                          │  │
│ └─────────────┘ └────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Evaluate]  /help  /practice  /ask  /examples  /evaluate  /hint  /more  /quit│
└──────────────────────────────────────────────────────────────────────────────┘
```

The input area SHALL be a multi-line text area (not a single-line input) to
support writing longer questions, code snippets, or detailed requests. The user
SHALL be able to press Enter to add new lines and Ctrl+Enter (or a configurable
keybinding) to submit.

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
