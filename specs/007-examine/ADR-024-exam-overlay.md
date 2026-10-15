# ADR-024 — exam-init as an Evaluation Overlay

## Status
Accepted

## Decision

Create `exam-init` / `exam-finish` as an exam lifecycle/orchestration layer that reuses the
`006-evaluate` evidence pipeline, tooling, deterministic rubric infrastructure,
structured LLM validation, and persistence.

It must not duplicate the project-analysis and evaluation implementations.

## Rationale

Ordinary `evaluate` answers:

> How does this project satisfy an exercise or structural evaluation?

`exam-init` / `exam-finish` answers:

> How did this student perform in a bounded exam, including the implementation,
> documentation, time, and use of tutoring assistance?

The exam workflow therefore requires lifecycle and process evidence in addition
to project evidence.

## Consequences

Positive:

- shared evidence and tooling;
- consistent deterministic scoring;
- less duplicated code;
- exam-specific PDF reporting;
- auditable exam lifecycle.

Negative:

- additional state model;
- exam-specific rubric configuration;
- event tracking for ask usage and duration.
