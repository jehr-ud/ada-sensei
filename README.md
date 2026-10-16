# ADA Sensei

ADA Sensei is an AI-powered educational coding agent focused on Android
development. It supports guided practice, contextual question and answer,
teachable examples, and evidence-based project evaluation — acting as a tutor
rather than a code generator.

## Features

- `/practice` — generate adaptive exercises based on current stage and learning gaps.
- `/ask` — contextual Q&A with progressive assistance (`/hint`, `/more`, `/solution`).
- `/examples` — teachable Android examples tailored to the current stage.
- `/evaluate` — evidence-based project evaluation (build, unit tests, Android Lint, Detekt).
- `/exam-init` / `/exam-finish` — exam workflow with timed attempts and detailed reports.
- `/learn` — review stage concepts and learning objectives.
- `/diagnose` — run a diagnostic to identify strengths and gaps.
- `/language` / `/lang` — view or change interface language (`es-CO` or `en-US`).
- Bilingual support (Spanish/English) for UI, stages, rubrics, and reports.
- Autonomous agent orchestration (Teacher + Planner + Evaluator + Trainer).
- Dynamic Basic Android Application project generation tailored to the learner.

## Prerequisites

- Python >= 3.11
- macOS or Linux (POSIX)
- JDK 17+ (required only for `/evaluate`)
- An Android project using the Gradle wrapper (`./gradlew`) for `/evaluate`

## Installation (Development / Editable)

For local development (recommended if you're working on the codebase):

```bash
# Clone the repository
git clone https://github.com/jehr-ud/ada-sensei.git
cd ada-sensei

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Reinstalling / Updating in dev mode

If you've made changes to dependencies or want to ensure everything is up to date:

```bash
cd ada-sensei
source .venv/bin/activate
pip install -e ".[dev]"  # Reinstalls in editable mode
```

To reinstall from scratch:

```bash
cd ada-sensei
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Note:** Reinstalling the virtual environment (`rm -rf .venv`) does not delete user data. ADA Sensei stores user data in `~/.local/share/ada-sensei/` and configuration in `~/.config/ada-sensei/`. To completely reset (including user progress, language preference, and history), delete those directories:

```bash
rm -rf ~/.local/share/ada-sensei ~/.config/ada-sensei
```


## Installation (GitHub only)

ADA Sensei installs directly from its GitHub repository — no PyPI publication is
required:

```bash
pip install git+https://github.com/jehr-ud/ada-sensei.git
```

To install from a specific tag or branch:

```bash
pip install "git+https://github.com/jehr-ud/ada-sensei.git@v0.1.0"
```

Verify the command is available:

```bash
ada-sensei /help
```

## Usage (Development)

Verify the CLI is available and launch the interactive session:

```bash
ada-sensei /help
ada-sensei
```

Run the test suite and lint:

```bash
pytest
ruff check .
```

## Default LLM (automatic provisioning)

ADA Sensei uses **Ollama** with the **`qwen2.5-coder:7b`** model as the default
LLM. On the first use of any LLM-dependent action it automatically:

1. detects whether the Ollama server is available;
2. installs and starts Ollama when missing (Homebrew on macOS, the official
   installer on Linux);
3. pulls the default model (`ollama pull qwen2.5-coder:7b`) when absent;
4. records the result so it does not repeat on every run.

A one-command installer performs the same setup:

```bash
curl -fsSL https://raw.githubusercontent.com/jehr-ud/ada-sensei/main/install.sh | bash
```

Any provisioning failure is reported as a limitation — never as a successful
setup. You can also configure a different provider/model under `[llm]` in the
config file (`~/.config/ada-sensei/config.toml`, see `ada-sensei config init`).

## Quick Start

```bash
ada-sensei            # enter your name at the welcome prompt (it is your identity)
> /practice --topic compose-state --difficulty intermediate
> /ask Why does LazyColumn not update?
> /examples ViewModel
> /evaluate --exercise exercise://<uuid>
```

## Architecture

ADA Sensei is organized as a layered Python application. The `specs/`
directory is the authoritative source of truth; code follows a
`SPEC → REQUIREMENT → DESIGN → TASK → IMPLEMENTATION → TEST → EVIDENCE`
workflow.

```
ada_sensei/
├── cli/                 # User interface layer
│   ├── main.py          #   bootstrap
│   ├── parser.py        #   input parsing
│   ├── commands.py      #   command definitions (Practice, Evaluate, …)
│   ├── router.py        #   dispatches commands to actions
│   ├── formatter.py     #   output formatting
│   ├── app.py, shell.py #   plain CLI shells
│   └── tui/             #   Textual TUI (screens, widgets, bindings)
├── actions/             # Command implementations
│   ├── base.py          #   action base class
│   ├── practice.py      #   /practice
│   ├── evaluate.py      #   /evaluate (Gradle, Lint, detekt)
│   ├── ask.py           #   /ask
│   └── examples.py      #   /examples
├── llm/                 # LLM integration
│   ├── base.py          #   provider interface
│   ├── ollama.py        #   Ollama provider
│   ├── pipeline.py      #   LLM → parser → validation → retry (max 3)
│   ├── validation.py    #   schema validation of model output
│   └── context.py       #   prompt/context building
├── storage/             # Persistence
│   ├── json_store.py    #   JSON-backed store
│   ├── attempts.py      #   attempt history
│   ├── exercises.py     #   exercise repository
│   ├── results.py       #   evaluation results
│   └── history.py       #   session/session history
├── tools/               # Low-level utilities
│   ├── discovery.py     #   Android project detection
│   ├── inspector.py     #   read-only project inspection
│   └── subprocess.py    #   Gradle execution wrapper
├── config/paths.py      # Config file paths
├── setup/provision.py   # LLM provisioning (Ollama install/pull)
├── models.py            # Domain models & identities
├── urns.py              # URN helpers (student/project/exercise/attempt)
└── context.py           # Execution/session context
```

### Layering and flow

A command travels through the stack as follows:

```
Input → parser → command object → router → action → LLM/storage/tools → result → formatter → output
```

1. The UI layer (`cli/parser.py`) turns raw input into a typed command object.
2. The `router` (`cli/router.py`) selects the right action and dispatches it.
3. Actions (`actions/`) orchestrate the domain logic, calling the LLM
   pipeline (`llm/`), repositories (`storage/`), and read-only project tooling
   (`tools/`) as needed.
4. Structured LLM output follows
   `LLM → parser → schema validation → retry → final failure`, with a maximum
   of three total attempts (one initial plus at most two retries); malformed or
   incomplete output is never silently accepted.
5. `formatter.py` converts the typed result into displayable text for either
   the plain CLI or the TUI.

In the TUI (`cli/tui/app.py`), non-blocking commands run on a worker thread and
report back through a done callback. `/evaluate` requires explicit confirmation
before any Gradle execution.

### Identity model

Student identity is never inferred from prompt content. The following
identifiers are kept separate throughout: `student_id`, `project_id`,
`exercise_id`, and `attempt_id` (managed via `urns.py`).

### Evaluation

`/evaluate` inspects the project read-only (`tools/`), requires confirmation
before running Gradle, and treats missing evidence as a limitation — never as
success. The top-level rubric is fixed at 40% functional requirements, 20%
tests, 15% code quality, 15% architecture, and 10% Android practices.

## Documentation

The authoritative specifications live in `specs/` (requirements, design,
tasks, and architecture decisions). See `specs/000-project/spec.md` for the
project overview and `specs/001-foundation/spec.md` for the shared
infrastructure, including LLM provisioning.