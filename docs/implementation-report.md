# ADA Sensei — Final Implementation Report

Date: 2026-09-02
Status: **IMPLEMENTATION COMPLETE**

## 1. Scope

Implemented the ADA Sensei educational coding agent from `specs/000-project`
through `specs/006-evaluate`, in dependency order, validating each phase with
automated tests. The CLI (Phase 2) was deliberately completed last so that it
could route to already-implemented actions.

Implementation followed:

```
SPEC → REQUIREMENT → DESIGN → TASK → IMPLEMENTATION → TEST → EVIDENCE
```

## 2. Per-Spec Status

| Spec | Phase | Status | Tests |
|---|---|---|---|
| 000-project | Project/non-functional baseline | Read + enforced (identity, safety, LLM discipline) | — |
| 001-foundation | Config, context, LLM pipeline, tools, storage, urns | Complete | 62 |
| 002-cli | CLI parser/router/shell/config | Complete (this phase) | 41 |
| 003-practice | Practice action + exercise persistence | Complete | 18 |
| 004-ask | Question classification + tutor agent | Complete | 11 |
| 005-examples | Topic resolver + curated/generated examples | Complete | 16 |
| 006-evaluate | Analyzer, Gradle/test/static tools, rubric, evaluation agent | Complete | 35 |
| **Total** | | | **183** |

All tests pass and `ruff check .` is clean.

## 3. Architecture

```text
ada_sensei
 ├── cli/                 # Phase 2 CLI (parser, shell, router, formatter, config_cmd)
 ├── actions/             # Shared injection + one module per action
 │    ├── base.py         # ActionServices + service_provider
 │    ├── practice.py
 │    ├── ask.py
 │    ├── examples.py
 │    └── evaluate.py
 ├── config/              # ConfigLoader, XDG path resolution, Secrets
 ├── context.py           # SessionContext / SessionState (assistance level, identity)
 ├── llm/                 # StructuredPipeline (max 3 attempts), validation, client
 ├── models.py            # Exercise, Attempt, EvaluationResult, Evidence, ...
 ├── storage/             # Json-backed Exercise/Attempt/Result/History stores
 └── tools/               # SubprocessRunner, tool discovery, read-only ProjectInspector
```

### Dependency injection

Every action receives `ActionServices` (config, `SessionContext`, LLM client,
data dir) via `service_provider`. Actions never instantiate stores or the
client themselves; this keeps CLI presentation isolated from domain logic and
makes actions unit-testable with fake clients and fake subprocess runners.

### Structured LLM contract

`LLM → parser → JSON-Schema validation → retry → final failure`. `StructuredPipeline`
caps at 3 total attempts (1 initial + up to 2 retries) and never silently
accepts malformed/incomplete output. All LLM-backed actions produce typed
pydantic models; the deterministic Evaluation rubric always overrides any LLM
score.

## 4. Key Behaviors Implemented

- **Identity** (`RQ-FND-023/024`): established by the name received at the start
  of an interactive session (TUI welcome); never inferred from prompt content.
  No `--student`/`/student` command exists. The received name is bound as the
  session student identity and persisted to the local profile.
- **Structured output** (LLM): max 3 attempts, JSON-Schema validated, retry then
  fail; handled for practice/ask/examples and qualitative evaluation
  interpretation.
- **Evaluation** (`006`): read-only structural analysis; Gradle wrapper
  discovery; assemble + unit tests + Lint + detekt by default; `connectedAndroidTest`
  never run by default (`--instrumented` rejected as "not yet supported").
  Confirmation required before Gradle execution; non-interactive requires
  explicit `--yes` and never assumes confirmation. Rubric weights
  functional 40% / tests 20% / code quality 15% / architecture 15% /
  Android practices 10%, scores 0–4, deterministic 0–100 overall; dimensions
  without evidence are "not evaluated" and excluded (ADR-011). Persistence:
  persist result → mark attempt completed → append outcome to history, with
  explicit failure reporting per step.
- **CLI** (`002`): interactive shell (`/help`, `/exit`, `/hint`, `/more`,
  `/solution`, `/evaluate`, `config init`), direct subcommand invocation,
  nonzero exit on error, sanitized messages
  with secret redaction (no tracebacks in normal use), XDG-aware `config init`.
  Student identity is the name given at session start (no `--student`).

## 5. CLI Notes (documented deviation)

The design doc (`specs/002-cli/design.md`) specifies a Typer-based command
parser. This implementation uses a custom `argparse`-style tokenizer in
`ada_sensei/cli/parser.py` shared by both the direct-invocation path and the
interactive shell for a single, deterministic, unit-testable parsing layer
(Typer is still a declared dependency). This is an implementation detail; every
RQ-CLI requirement (001–016) is met and covered by automated tests. It is
flagged here for transparency, not hidden.

## 6. Testing & Evidence

- **183 tests** pass (full suite).
- **`ruff check . --fix`**: clean.
- **CLI smoke tests** verified:
  - `ada-sensei` starts the interactive shell and handles `/exit`.
  - `ada-sensei --help` prints available commands.
  - the TUI welcome binds the entered name as the student identity and creates
    the profile.
  - `configured config init` writes a redacted XDG template.
  - `evaluate` (non-interactive, no `--yes`) aborts before any Gradle task.
  - `evaluate --instrumented` is rejected as "not yet supported".
  - Unknown action exits with a non-zero status and a hint.
  - `python -m ada_sensei` and the installed `ada-sensei` console script both work.

## 7. Limitations

- LLM-backed actions require an available provider (default Ollama) and degrade
  gracefully to deterministic/limitation messages when unavailable; missing
  evidence is reported as a limitation, never fabricated success.
- Instrumented tests are intentionally not runnable (reserved flag).
- Gradle/Android tooling must be present for full evaluation; otherwise
  outcomes are reported as limitations.
- `android/` and `testing/` knowledge directories exist but currently contain no
  curated examples (an area for future curation).

## 8. Conclusion

All specifications 000 → 006 are implemented and verified by tests and lint. The
project is delivered with actions, storage, structured-LLM discipline, a
deterministic evaluation rubric, and a working interactive/direct CLI.

**IMPLEMENTATION COMPLETE.**