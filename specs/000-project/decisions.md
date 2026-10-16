# Architecture Decisions

## ADR-001 — CLI First

ADA Sensei will initially be a command-line application. This minimizes infrastructure and makes it suitable for local development environments and classroom workshops.

## ADR-002 — LLM as Replaceable Dependency

The application SHALL not depend directly on a specific model. An `LLMClient` abstraction will allow Ollama and future providers/models to be swapped.

## ADR-003 — Evidence Before Evaluation

Project evaluation SHALL collect objective evidence such as build results, test results, project structure, and static-analysis findings before asking the LLM to produce pedagogical feedback.

## ADR-004 — Specs as Source of Truth

Specifications are part of the development workflow, not only documentation. Implementation tasks must trace back to requirements.

## ADR-005 — Android as First Domain

The architecture SHALL isolate Android-specific capabilities so the pedagogical engine can later support other programming domains.

## ADR-006 — Foundation Specification

All cross-cutting concerns (configuration, LLM abstraction, structured-output
validation, domain models, persistence, shared context, deterministic tools,
runtime requirements) SHALL be owned by `specs/001-foundation`. No action
specification SHALL redefine them.

## ADR-007 — Runtime and Stack

The application SHALL run on Python >= 3.11 (typing: type hints required).
JVM-based tooling SHALL be executed as subprocesses (Gradle, detekt, Android
Lint); the application does not embed a JVM. Gradle repository wrappers are
preferred over system Gradle. Default subprocess timeout is 600 s.

## ADR-008 — Structured LLM Output

Structured results SHALL be produced via JSON output with JSON-Schema
validation. The pipeline permits a maximum of 3 total attempts: 1 initial
attempt plus up to 2 retries. On exhaustion of the final allowed attempt the
action fails cleanly; malformed or incomplete output is never silently accepted.

## ADR-009 — Local Persistence and Stable IDs

Persistence SHALL be local JSON documents under XDG-conformant directories
(data: `$XDG_DATA_HOME/ada-sensei/`, fallback `~/.local/share/ada-sensei/`),
written atomically and versioned. Persisted objects use URN ids (`student://`,
`project://`, `exercise://`, `attempt://`, `result://`), and exercise
requirements use stable `req://<uuid>` ids so that `/evaluate` can map evidence
to requirements over time. `student_id`, `project_id`, `exercise_id`, and
`attempt_id` are distinct identifiers and SHALL NEVER be conflated.

## ADR-010 — Progressive Assistance Standard

Assistance is a single graded scale maintained by the session
(`guiding_question → hint → conceptual_explanation → code_fragment → solution`).
All pedagogical actions honor it, and CLI commands `/hint`, `/more`, and
`/solution` advance it.

## ADR-011 — Evidence Sufficiency

A criterion without evidence is "not evaluated", never assumed to pass or fail.
Missing or failed build/test/static-analysis execution SHALL be reported as a
limitation and may exclude the affected criteria from the score denominator.

## ADR-012 — Initial Static Analysis Tools

Kotlin quality is checked with **detekt**; Android/Compose issues with
**Android Lint**. Both run through the project's Gradle wrapper and are
pluggable/configurable (see 001-foundation config `[tools]`). Findings carry a
severity of `ERROR`, `WARNING`, or `INFO`. Static-analysis findings are
evidence and SHALL NOT automatically map one-to-one to grade deductions; they
feed the rubric, which the LLM interprets.

## ADR-013 — Credentials via Environment

API credentials SHALL be read from the environment (`ADA_SENSEI_API_KEY` by
default) and never echoed in logs or normal output.

## ADR-014 — Context Budget Management

All LLM calls pass through the `ContextManager`, which enforces a configurable
token budget. It first performs deterministic reduction/eviction using a
documented priority policy. Optional LLM summarization may occur only after
deterministic reduction, must be marked LLM-derived, and always surfaces a
notice when context was reduced or summarized.

## ADR-015 — Name-Based Student Identity

Student identity is established by a name the student provides at the start of
an interactive session (the TUI welcome greeting) and is never inferred from
prompt content. No `--student`/`/student` option or command exists; the provided
name becomes the current `student_id`. If the student record does not exist, it
is created after the name is received. The last used name is remembered in the
data directory so later runs do not re-ask; the student can update the identity
with `/name <name>`. Identity SHALL be kept as separate fields: `student_id`,
`project_id`, `exercise_id`, `attempt_id`.

## ADR-016 — Evaluation Execution Safety and Default Scope

`/evaluate` SHALL require confirmation before executing Gradle-based tasks.
The default evaluation runs: project inspection, the Gradle build/compile,
unit tests, Android Lint, and detekt. `connectedAndroidTest` (instrumented
tests) SHALL NOT run by default; it is reserved for a future explicit
`--instrumented` option.

## ADR-017 — Initial Evaluation Rubric Weights

The initial top-level rubric weights are: Functional requirements 40%, Tests
20%, Code quality 15%, Architecture 15%, Android practices 10%. Exercise-level
functional requirement criteria are subcriteria inside the fixed 40% dimension;
their normalized subweights sum to 100% of that dimension and never create
additional top-level weight. Scoring is deterministic wherever objective
evidence exists; the LLM interprets evidence but SHALL NOT invent it.

## ADR-018 — Attempt Completion and Evaluation History

A successfully completed evaluation for a known attempt marks that attempt as
completed and appends the evaluation outcome to student history. These updates
use foundation persistence interfaces and preserve all four identity fields.

## ADR-019 — Non-Interactive Evaluation Confirmation

Non-interactive `evaluate` execution requires an explicit `--yes` confirmation
override before any Gradle-based task is executed.

## ADR-020 — Default LLM Provisioning and GitHub-Only Distribution

The default LLM is the Ollama provider with the `qwen2.5-coder:7b` model
(RQ-FND-029). The package SHALL be installable directly from the GitHub
repository via `pip install git+https://github.com/jehr-ud/ada-sensei.git`
without PyPI (RQ-FND-031). Because pip cannot reliably run privileged
post-install hooks, automatic provisioning of the Ollama server and the default
model (RQ-FND-030) runs on first use of an LLM-dependent action, or through an
optional one-command installer script. Provisioning failures are reported as
limitations, never as success.


## ADR-021 — Teacher-Led Multi-Agent Orchestration

Every student-facing action SHALL be coordinated by a principal `TeacherAgent`
and invoke the three specialist subagents `PlannerAgent`, `EvaluatorAgent`, and
`TrainerAgent`. Specialists return typed, bounded outputs; the Teacher resolves
conflicts, chooses the next pedagogical step, and presents one coherent response.
The agents do not independently mutate shared state; persistence is performed by
application services after validated decisions.

## ADR-022 — Configurable Mastery Learning Across Domains

Learning stages, competencies, assessment dimensions, progression gates, and
rubrics SHALL be data-driven and versioned in JSON. Android is the first domain;
future subjects SHALL be able to supply a different catalog without changing the
mastery engine. Each stage is evaluated across construction, analysis/design, and
comprehension, with configurable critical competencies and minimum thresholds.

## ADR-023 — Separate Study Progression from Exams

A mastery evaluation is a progression decision, not the same thing as a formal
exam. Exams may be initiated at any stage and use `/exam-init` and `/exam-finish`;
exam outcomes are stored separately and do not silently change the current stage.
