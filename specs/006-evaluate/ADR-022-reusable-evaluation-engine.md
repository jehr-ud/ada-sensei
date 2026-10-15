# ADR-022 — Reusable Evaluation Engine

## Status

Accepted

> Renumbered from ADR-020 to avoid colliding with `specs/000-project/decisions.md`; content unchanged.

## Context

`007-examine` needs the same Android project evidence used by `/evaluate`:
project inspection, Gradle execution, unit tests, Android Lint, Detekt, requirement
matching, and deterministic scoring mechanics.

Duplicating these components in `007-examine` would create divergent evidence
collection and scoring behavior.

## Decision

Introduce a reusable `EvaluationEngine` abstraction below `EvaluateAction`.

`EvaluateAction` remains the workflow adapter for `/evaluate`.

Higher-level workflows MAY consume the engine directly.

The engine SHALL expose reusable evidence collection, requirement matching, rubric
mechanics, and structured interpretation.

## Consequences

Positive:

- evidence collection is implemented once;
- `evaluate` and `exam-init` / `exam-finish` use the same Android analysis;
- future evaluation workflows can reuse the engine;
- tests can target the engine independently.

Constraint:

- the engine must not depend on CLI/TUI concerns;
- workflow-specific lifecycle and reporting remain outside the engine.
