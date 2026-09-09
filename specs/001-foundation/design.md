# Design

## Components

```text
ada_sensei/
├── config.py               # ConfigLoader, Secrets
├── models.py               # core domain models
├── llm/
│   ├── base.py             # LLMClient abstraction
│   ├── ollama.py           # OllamaProvider (OpenAI-compatible)
│   ├── validation.py       # JSON-Schema validator
│   ├── pipeline.py         # StructuredPipeline (request -> validate -> retry)
│   └── context.py          # ContextManager (token budget, eviction)
├── storage/
│   ├── json_store.py       # versioned, atomic JSON store + URNs
│   ├── history.py          # StudentProfile/HistoryStore
│   ├── exercises.py        # ExerciseStore
│   ├── attempts.py         # AttemptStore
│   └── results.py          # ResultStore
├── context.py              # SessionContext
├── setup/
│   └── provision.py        # DefaultModelProvisioner (Ollama + default model)
└── tools/
    ├── subprocess.py       # SubprocessRunner
    ├── inspector.py        # ProjectInspector (read-only)
    └── discovery.py        # gradlew/gradle, JDK, Android SDK discovery
```

## Configuration Schema

```toml
[project]
path = "."

[llm]
provider = "ollama"               # ollama | openai-compatible
model = "qwen2.5-coder:7b"
base_url = "http://localhost:11434/v1"
temperature = 0.2
timeout_seconds = 120
max_output_tokens = 2048
max_context_tokens = 8192
max_attempts = 3                  # structured-output attempts (ADR-008)

[llm.context]
conversation_budget = 0.4         # share of max_context_tokens
evidence_budget = 0.4

[tools]
timeout_seconds = 600
network = true
offline = false
static_kotlin = "detekt"
static_android = "lint"

[storage]
data_dir = "$XDG_DATA_HOME/ada-sensei"     # fallback ~/.local/share/ada-sensei
config_dir = "$XDG_CONFIG_HOME/ada-sensei" # fallback ~/.config/ada-sensei
cache_dir = "$XDG_CACHE_HOME/ada-sensei"   # fallback ~/.cache/ada-sensei

[secrets]
api_key_env = "ADA_SENSEI_API_KEY"
```

Precedence: CLI overrides > environment variables (prefix `ADA_SENSEI_`) >
config file (default `$XDG_CONFIG_HOME/ada-sensei/config.toml`, fallback
`~/.config/ada-sensei/config.toml`) > defaults.
Explicit overrides `ADA_SENSEI_DATA_DIR`, `ADA_SENSEI_CONFIG`, and
`ADA_SENSEI_CACHE_DIR` take precedence over XDG (RQ-FND-025).

## Credential Handling

Secrets are read only from `ada_sensei.config.Secrets` which checks the
configured environment variable. A `Secret.redact(text)` utility replaces
credential values in any captured output before it is logged or shown.

## LLM Client

```text
LLMClient (abstract)
 ├── chat(messages) -> str
 └── chat_structured(messages, model, json_schema) -> Model
```

`StructuredPipeline` orchestrates the structured path:

```text
prompt + schema
   ↓
provider.request(format="json")
   ↓
parse
   ↓ validate (Pydantic + JSON Schema)
   ├─ invalid -> re-prompt with validator message  (max 3 attempts total)
   └─ exhausted -> raise StructuredOutputError (clean, user-presentable)
```

The pipeline permits a maximum of 3 total attempts: 1 initial attempt plus up
to 2 retries. A lower configured maximum may be used, but a value above 3 is
invalid. The pipeline NEVER returns partially validated output
(ADR-008, RQ-FND-008).

## Domain Models (core attributes)

```text
AssistanceLevel = guiding_question | hint | conceptual_explanation | code_fragment | solution

Difficulty = beginner | intermediate | advanced

StudentProfile
- student_id: student://<uuid>
- history: exercises attempted, success/failure, hints requested, recurring errors,
           strengths, weaknesses

Exercise
- id: exercise://<uuid>
- title, topic, difficulty, objective, statement
- requirements: [Requirement]      # id: req://<uuid>  (stable)
- constraints: [str]
- hints: [str]                     # progressive: hint 1..n
- evaluation_criteria: [Criterion] # requirement_id, dimension, weight
- source: generated | curated
- created_at

Attempt
- id: attempt://<uuid>
- student_id, project_id, exercise_id | None
- assistance_level, hints_used, conversation_ref
- started_at, status: in_progress | completed

Evidence
- source: build | test | lint | detekt | file | llm
- type: compilation | unit_test | android_lint | detekt | structure | requirement
- severity: error | warning | info | null   # static-analysis findings
- status: pass | fail | skipped | missing
- message, file, line, command

EvaluationCriterion
- requirement_id: req://<uuid> | None for top-level criteria
- dimension: functional_requirements | tests | code_quality | architecture | android_practices
- weight: normalized subweight within its parent dimension when used as a
  per-exercise subcriterion
- score: 0..4 | None (not evaluated)
- evidence: [Evidence]

EvaluationResult
- id: result://<uuid>, attempt_id, exercise_id?, student_id?
- overall_score: 0..100 | None
- criteria: [EvaluationCriterion]
- strengths, weaknesses, feedback, recommendations, next_learning_activity
- created_at
```

Identifiers: `student_id` (`student://`), `project_id` (`project://`, derived
from the project path hash), `exercise_id` (`exercise://`), `attempt_id`
(`attempt://`) are distinct and never conflated (ADR-009).

## Persistence

`JsonStore` provides `read(uri)`/`write(uri, obj)`:

- versioned documents (`{"schema": 1, ...}`);
- atomic writes (temp file + rename);
- URN routing under the XDG data directory (ADR-009):
  `student://<id>` -> `history/<id>.json`, `exercise://<id>` ->
  `exercises/<id>.json`, `attempt://<id>` -> `attempts/<id>.json`,
  `result://<id>` -> `results/<id>.json`.

## Student Identity Flow

- The name the student provides at the start of an interactive session (the TUI
  welcome greeting) sets `SessionContext.student_id`; identity is never parsed
  from prompts, options, or commands (ADR-015).
- On first use, `HistoryStore.has(student_id)` is checked; if absent, the
  `StudentProfile` is created from the received name (RQ-FND-024).

## Session Context

```text
SessionContext
- config: Config
- project: ProjectRef       # active project path
- student_id: str | None
- project_id: str | None     # derived deterministic id for the project
- attempt_id: str | None
- conversation: list[Turn]  # bounded
- assistance_level: AssistanceLevel
- current_exercise_id: str | None
```

Sessions persist to `sessions/<student_id>.json` on exit and are reloaded on
start (RQ-FND-016).

## Subprocess Runner

`SubprocessRunner.run(cmd, cwd, timeout, env)` returns an `Evidence`-compatible
result (exit code, stdout, stderr, duration). A timeout sets
`status=missing` with a limitation message (never success).

## Context Manager

Budget split: conversation | evidence | output.

When the budget is exceeded, the manager first applies deterministic reduction
using a fixed priority order. Identity and active-task context are preserved
before lower-priority history. Only if the reduced context still exceeds the
budget MAY the manager request an LLM summary.

LLM-generated summaries are marked `llm_derived=true` and are not objective
evidence. The manager returns reduction metadata and a notice in
`chat_context()`.

## Tool Discovery

`discovery.find_gradle(project)` -> `./gradlew` first, then `gradle`.
`discovery.find_jdk()` -> `JAVA_HOME` or `java` on PATH; version-checked >= 17.
`discovery.find_sdk()` -> `ANDROID_HOME`/`ANDROID_SDK_ROOT`/`local.properties`.
Missing tools produce `ToolUnavailable` entries reported as limitations
(RQ-FND-019).

## Default LLM Provisioning

`DefaultModelProvisioner` (RQ-FND-029/030):

```text
LLM required by an action
   ↓
provision_if_needed()
   ├── Ollama reachable at base_url?
   │    ├── yes → model present?
   │    │         ├── yes → done (recorded)
   │    │         └── no  → ollama pull qwen2.5-coder:7b
   │    └── no  → install Ollama (brew on macOS / official script on Linux),
   │              start it, then pull the default model
   ↓
outcome recorded (config/cache) → subsequent runs skip
failure → reported as limitation, never success
```

- Runs automatically on first use of any LLM-dependent action; the optional
  `install.sh` at the repository root performs the same steps for one-command
  setup.
- The provisioning outcome is recorded so it does not repeat on every invocation.
- Model pull uses the default model `qwen2.5-coder:7b` unless configured
  otherwise.