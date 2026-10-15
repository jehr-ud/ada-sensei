# ADR-023 — Rubric Definition Abstraction

## Status

Accepted

> Renumbered from ADR-021 to avoid colliding with `specs/000-project/decisions.md`; content unchanged.

## Context

`/evaluate` uses a fixed rubric:

- functional requirements 40%;
- tests 20%;
- code quality 15%;
- architecture 15%;
- Android practices 10%.

`007-examine` requires a different rubric that also considers examination-specific
metrics.

The scoring mechanics should be shared without forcing all workflows to use the
same dimensions or weights.

## Decision

Separate:

```text
RubricEngine
```

from:

```text
RubricDefinition
```

The `/evaluate` workflow uses:

```text
evaluate-default:v1
```

Other workflows define their own versioned rubric.

A workflow SHALL NOT mutate another workflow's rubric definition.

## Consequences

- deterministic scoring remains centralized;
- rubric weights remain explicit and versioned;
- exam scoring can add exam-specific dimensions without changing `/evaluate`;
- historical results can identify the rubric version used.
