# Requirements

## RQ-FND-001 Configuration

The system SHALL resolve configuration from defaults, an optional config file,
environment variables, and CLI overrides, in that order of precedence.

## RQ-FND-002 Project path

The system SHALL expose the active project/workspace path through configuration.

## RQ-FND-003 LLM configuration

The system SHALL allow the LLM provider, base URL, and model to be configured
without code changes.

## RQ-FND-004 Credential handling

Secrets SHALL be read only from the environment variable `ADA_SENSEI_API_KEY`
(or the configured `api_key_env` variable), and SHALL be redacted from all
logs and normal output.

## RQ-FND-005 LLMClient abstraction

Business logic SHALL interact with the LLM through the `LLMClient` abstraction
and SHALL not depend on a specific provider.

## RQ-FND-006 Structured output

`LLMClient` SHALL support structured output for a given JSON Schema, validated
against that Schema.

## RQ-FND-007 Ollama provider

The system SHALL provide an Ollama provider as the default provider, accessed
through its OpenAI-compatible endpoint.

## RQ-FND-008 Validation failure behavior

The structured-output pipeline SHALL allow a maximum of 3 total validation
attempts: 1 initial attempt plus up to 2 retries. Validation errors MAY be fed
back to the model on retries. If the final allowed attempt fails validation,
the pipeline SHALL fail with a clear user-presentable error and no partial
data. A fourth attempt SHALL NOT occur. The system SHALL never silently accept
malformed or incomplete structured output.

## RQ-FND-009 Domain models

Core domain models (Topic, Difficulty, AssistanceLevel, StudentProfile,
Exercise, Requirement, Attempt, Evidence, EvaluationCriterion, EvaluationResult,
PracticeResult, Answer, Example) SHALL be defined centrally in one module.

## RQ-FND-010 Stable identifiers

Every persisted model SHALL carry a stable identifier; requirements within an
exercise SHALL carry a stable `requirement_id` usable across time and contexts.

## RQ-FND-011 Student history persistence

The system SHALL persist and reload student profile/history, recording exercises
attempted, success/failure, hints requested, recurring errors, and completed
evaluation outcomes.

## RQ-FND-012 Exercise persistence

The system SHALL persist exercises and SHALL retrieve them by stable id.

## RQ-FND-013 Evaluation result persistence

The system SHALL persist evaluation results and SHALL retrieve them by stable id.

## RQ-FND-014 Storage safety

Persistence SHALL be local, versioned, atomically written, and SHALL never
modify the student's project directory.

## RQ-FND-015 Session context

A shared session context SHALL hold configuration, active project, student,
bounded conversation, assistance level, and current exercise.

## RQ-FND-016 Assistance level persistence

The current assistance level SHALL be maintained in the session and SHALL
survive session restarts for the same student and exercise.

## RQ-FND-017 Subprocess timeouts

The subprocess runner SHALL enforce configurable timeouts and SHALL report a
timeout as a limitation rather than success.

## RQ-FND-018 Read-only inspection

Project inspection tools SHALL be read-only; no action may require write access
to the student project for inspection.

## RQ-FND-019 Tool discovery

Gradle wrapper, JDK, and Android SDK SHALL be auto-discovered; missing tooling
SHALL be reported as a limitation, not silently skipped.

## RQ-FND-020 Context budget

LLM calls SHALL respect a configurable context budget. When the budget is
exceeded, the ContextManager SHALL first apply deterministic eviction/reduction
using a documented priority policy. Optional LLM summarization MAY occur only
after deterministic reduction and SHALL be explicitly marked as LLM-derived.
The system SHALL emit a visible notice whenever context was reduced or
summarized.

## RQ-FND-021 Runtime declaration

The system SHALL declare its runtime requirements (Python >= 3.11, JDK 17+,
Gradle wrapper preferred, default subprocess timeout 600 s) in its packaging.

## RQ-FND-022 Identity separation

The system SHALL treat `student_id`, `project_id`, `exercise_id`, and
`attempt_id` as distinct identifiers; `project_id` SHALL be derived
deterministically from the project path (ADR-009).

## RQ-FND-023 Student identity source

Student identity SHALL be set from the name the student provides at the start
of an interactive session (the TUI welcome greeting) and SHALL NOT be inferred
from prompt content, files, environment variables, or conversational content.

## RQ-FND-024 Student record creation

If the student record for a given `student_id` does not exist, the system SHALL
create the local record only after explicit user confirmation.

## RQ-FND-025 XDG storage layout

Data, configuration, and cache SHALL be stored under XDG-conformant directories
(`$XDG_DATA_HOME|CONFIG_HOME|CACHE_HOME` with `~/.local/share`,
`~/.config`, `~/.cache` fallbacks), with `ADA_SENSEI_DATA_DIR` /
`ADA_SENSEI_CONFIG` / `ADA_SENSEI_CACHE_DIR` as explicit overrides.

## RQ-FND-026 Attempt persistence

The system SHALL persist `Attempt` records independently from `Exercise` records
and SHALL retrieve them by stable `attempt://<uuid>` id. An attempt SHALL bind
`student_id`, `project_id`, and `exercise_id` when an exercise is present, and
its lifecycle status SHALL be persisted.

## RQ-FND-027 Context reduction priority

The ContextManager SHALL preserve identity and active-task context before
lower-priority conversation or history when reducing context.

## RQ-FND-028 Context reduction metadata

The ContextManager SHALL expose whether context was evicted, reduced, or
LLM-summarized so downstream actions can report the reduction when relevant.

## RQ-FND-029 Default LLM model

The system SHALL declare a default LLM provider and model used when none is
configured: the Ollama provider with the `qwen2.5-coder:7b` model through its
OpenAI-compatible endpoint (RQ-FND-007).

## RQ-FND-030 Automatic LLM provisioning

When the default LLM toolchain (the Ollama server) or the default model is not
available, the system SHALL provision it automatically — installing Ollama and
pulling the default model — as part of installation or on first use of an
LLM-dependent action. Provisioning failures SHALL be reported as limitations;
the system SHALL never fabricate a successful setup.

## RQ-FND-031 GitHub-only distribution

The package SHALL be installable directly from its GitHub repository through
`pip install git+<repository-url>` without requiring publication to PyPI.

---

## Traceability

| Requirement | Component | Test |
|---|---|---|
| RQ-FND-001 | `ada_sensei.config.ConfigLoader` | `tests/config/test_loader.py::test_precedence` |
| RQ-FND-002 | `ada_sensei.config.ConfigLoader` | `tests/config/test_loader.py::test_project_path` |
| RQ-FND-003 | `ada_sensei.config.ConfigLoader` | `tests/config/test_loader.py::test_llm_settings` |
| RQ-FND-004 | `ada_sensei.config.Secrets` | `tests/config/test_secrets.py::test_env_only` / `test_redact` |
| RQ-FND-005 | `ada_sensei.llm.base.LLMClient` | `tests/llm/test_client.py::test_abstraction` |
| RQ-FND-006 | `ada_sensei.llm.base.LLMClient`, `ada_sensei.llm.validation.validate` | `tests/llm/test_structured.py::test_schema_validation` |
| RQ-FND-007 | `ada_sensei.llm.ollama.OllamaProvider` | `tests/llm/test_ollama.py::test_default_url` |
| RQ-FND-008 | `ada_sensei.llm.pipeline.StructuredPipeline` | `tests/llm/test_structured.py::test_retry/…test_exhaustion` |
| RQ-FND-009 | `ada_sensei.models` | `tests/models/test_models.py::test_required_fields` |
| RQ-FND-010 | `ada_sensei.models` | `tests/models/test_models.py::test_stable_ids` |
| RQ-FND-011 | `ada_sensei.storage.HistoryStore` | `tests/storage/test_history.py::test_roundtrip` |
| RQ-FND-012 | `ada_sensei.storage.ExerciseStore` | `tests/storage/test_exercises.py::test_get_by_id` |
| RQ-FND-013 | `ada_sensei.storage.ResultStore` | `tests/storage/test_results.py::test_roundtrip` |
| RQ-FND-014 | `ada_sensei.storage.JsonStore` | `tests/storage/test_json_store.py::test_atomic_write` / `test_no_project_write` |
| RQ-FND-015 | `ada_sensei.context.SessionContext` | `tests/context/test_session.py::test_holds_state` |
| RQ-FND-016 | `ada_sensei.context.SessionContext` | `tests/context/test_session.py::test_resume` |
| RQ-FND-017 | `ada_sensei.tools.SubprocessRunner` | `tests/tools/test_subprocess.py::test_timeout_is_limitation` |
| RQ-FND-018 | `ada_sensei.tools.ProjectInspector` | `tests/tools/test_inspector.py::test_read_only` |
| RQ-FND-019 | `ada_sensei.tools.discovery` | `tests/tools/test_discovery.py::test_missing_reported` |
| RQ-FND-020 | `ada_sensei.llm.context.ContextManager` | `tests/llm/test_context.py::test_budget_eviction` |
| RQ-FND-021 | `pyproject.toml`, `docs/runtime.md` | `tests/runtime/test_metadata.py::test_requires` |
| RQ-FND-022 | `ada_sensei.models`, `ada_sensei.storage.urns` | `tests/models/test_models.py::test_id_distinctness` |
| RQ-FND-023 | `ada_sensei.cli` → `SessionContext.student_id` | `tests/cli/test_student.py::test_identity_never_inferred` |
| RQ-FND-024 | `ada_sensei.storage.history` + CLI confirm | `tests/storage/test_history.py::test_create_requires_confirmation` |
| RQ-FND-025 | `ada_sensei.config.paths` | `tests/config/test_paths.py::test_xdg_layout` |
| RQ-FND-026 | `ada_sensei.storage.AttemptStore` | `tests/storage/test_attempts.py::test_roundtrip_and_status` |
| RQ-FND-027 | `ada_sensei.llm.context.ContextManager` | `tests/llm/test_context.py::test_identity_priority` |
| RQ-FND-028 | `ada_sensei.llm.context.ContextManager` | `tests/llm/test_context.py::test_reduction_metadata` |
| RQ-FND-029 | `ada_sensei.config` / `ada_sensei.llm.ollama` | `tests/llm/test_ollama.py::test_default_model` |
| RQ-FND-030 | `ada_sensei.setup.provision` | `tests/setup/test_provision.py::test_auto_install` / `test_failure_as_limitation` |
| RQ-FND-031 | `pyproject.toml` | `tests/runtime/test_metadata.py::test_github_install` |