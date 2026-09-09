# Foundation Specification

## Objective

Define the shared infrastructure used by the CLI and every action: configuration,
the LLM abstraction, structured-output validation, domain models, persistence,
shared session context, tooling, and runtime requirements.

Every action specification (002-cli through 006-evaluate) SHALL build on this
specification and SHALL NOT redefine the concepts owned here.

## 1. Scope

The foundation SHALL own:

- configuration loading and precedence;
- credential handling and redaction;
- `LLMClient` abstraction and the Ollama provider;
- structured LLM output validation;
- core domain models;
- persistence stores (student profile/history, exercises, attempts, evaluation results);
- the shared session context, including the progressive-assistance level;
- deterministic tooling: subprocess runner and read-only project inspection;
- runtime requirements and LLM context/token management.

## 2. Runtime Requirements

| Concern | Requirement |
|---|---|
| Language | Python >= 3.11, `< 4.0`, declared in `pyproject.toml` |
| OS | macOS and Linux for the MVP (POSIX); Windows not required |
| JDK | JDK 17+ required to execute Gradle builds (AGP 8.x baseline) |
| Android SDK | Discovered via `ANDROID_HOME` / `ANDROID_SDK_ROOT` or `local.properties`; used by Gradle, never invoked directly |
| Gradle | Prefer the repository wrapper (`./gradlew`); fall back to `gradle` on `PATH`; version constraints delegated to the Android Gradle Plugin |
| Subprocess timeout | Default 600 s per tool invocation, configurable; timeout is reported as a limitation, never as a pass |
| Network | Dependency resolution allowed by default; an offline mode disables it (config or `--offline`) |

## 3. LLM Providers

- **Ollama** is the first-class default provider. It SHALL be accessed through its
  OpenAI-compatible endpoint (`http://localhost:11434/v1` by default).
- **OpenAI-compatible** HTTP endpoints SHALL be supported generically so other
  local or remote providers can be configured without code changes (ADR-002).

## 4. Structured LLM Output

Actions produce structured data (`Exercise`, `EvaluationResult`, `Example`).
The foundation SHALL provide a validation pipeline that:

1. requests JSON output from the provider;
2. parses the response;
3. validates it against a JSON Schema derived from the target domain model;
4. on validation failure, re-prompts with the validator message;
5. allows a maximum of **3 total attempts** (1 initial attempt + up to 2 retries);
   a lower configured maximum MAY be used, but a value above 3 is invalid;
6. if the final allowed attempt fails, fails with a clear, user-presentable
   error and no partial data.

The system SHALL NEVER silently accept malformed or incomplete structured
output (ADR-008).

## 5. Domain Models

The foundation SHALL define, in one central Python module, the models shared
across actions:

- `Topic` and `Difficulty` (beginner | intermediate | advanced);
- `AssistanceLevel` (guiding_question | hint | conceptual_explanation | code_fragment | solution);
- `StudentProfile` (includes a compact history summary);
- `Exercise` and `Requirement` (stable `requirement_id`);
- `Evidence` (includes static-analysis `severity`);
- `EvaluationCriterion` and `EvaluationResult`;
- `Attempt` (binds `student_id`, `project_id`, `exercise_id`, and session state);
- `PracticeResult`, `Answer`, `Example`.

Every persisted model SHALL carry a stable identifier (see ADR-009).
`student_id`, `project_id`, `exercise_id`, and `attempt_id` SHALL be distinct
identifiers and SHALL never be conflated. `project_id` is derived deterministically
from the project path.

## 6. Persistence

Storage SHALL follow XDG conventions (ADR-009):

| Kind | Path |
|---|---|
| Data | `$XDG_DATA_HOME/ada-sensei/` (fallback `~/.local/share/ada-sensei/`) |
| Configuration | `$XDG_CONFIG_HOME/ada-sensei/` (fallback `~/.config/ada-sensei/`) |
| Cache | `$XDG_CACHE_HOME/ada-sensei/` (fallback `~/.cache/ada-sensei/`) |

The data directory SHALL contain:

```text
<data_dir>/
├── history/<student_id>.json
├── exercises/<exercise_id>.json
├── attempts/<attempt_id>.json
├── results/<result_id>.json
└── sessions/<student_id>.json    # session resume data (assistance level, conversation)
```

Stores SHALL be versioned, written atomically, and SHALL never write inside the
student's project. This is the persistence contract required by the
practice -> evaluate pipeline (see 003-practice and 006-evaluate).

## 7. Shared Context

A `SessionContext` SHALL hold: resolved configuration, active project path,
current student, conversation (bounded), current assistance level, and current
exercise id. All actions SHALL read from and update the session context instead
of carrying their own ambient state.

## 8. Deterministic Tools

- `SubprocessRunner` SHALL execute external commands (Gradle, lint, detekt,
  tests) with enforced timeouts, captured output, and a bounded environment.
- `ProjectInspector` SHALL provide read-only inspection (structure, source file
  reads, wrapper detection). Write operations SHALL not be required by Ask.

## 9. Context/Token Management

The `ContextManager` SHALL:

- respect a configurable `max_context_tokens` budget;
- first apply deterministic reduction/eviction using a documented priority policy;
- preserve identity and active-task context before lower-priority history;
- optionally summarize remaining over-budget context with the LLM only after
  deterministic reduction;
- mark any LLM-produced summary as LLM-derived rather than objective evidence;
- reserve separate allowances for conversation versus evidence;
- surface a notice and metadata whenever reduction or summarization occurred.

## 10. Default LLM Provisioning

- The default provider is **Ollama** and the default model is
  `qwen2.5-coder:7b` (RQ-FND-029). A different provider/model is configurable.
- The distribution SHALL be installable directly from the GitHub repository
  (`pip install git+https://github.com/jehr-ud/ada-sensei.git`) without PyPI
  (RQ-FND-031).
- Because pip cannot reliably run privileged post-install hooks, the automatic
  provisioning of the default LLM (RQ-FND-030) runs on first use of an
  LLM-dependent action (and through an optional one-command installer script):
  1. detect whether the Ollama server is reachable at the configured base URL;
  2. if not, install Ollama for the platform (Homebrew on macOS, the official
     installer on Linux) and start it;
  3. pull the default model (`ollama pull qwen2.5-coder:7b`) when absent;
  4. record the provisioning outcome so subsequent runs skip redundant work;
  5. report any failure as a limitation — never as a successful setup.

## 11. Out of Scope

Cloud multi-user platform, authentication, mobile UI, model training, and full
autonomous project modification remain out of scope (inherited from 000-project).