# ADA Sensei — Agent Instructions

## Source of Truth

The `specs/` directory is the authoritative source of truth for product
behavior, requirements, architecture, and implementation tasks.

Before implementing a specification, read its `spec.md`, `requirements.md`,
`design.md`, and `tasks.md`.

## Spec-Driven Development

Follow:

`SPEC → REQUIREMENT → DESIGN → TASK → IMPLEMENTATION → TEST → EVIDENCE`

Implement in dependency order. Do not silently reinterpret requirements. If a
requirement is contradictory or materially ambiguous, stop and report it before
implementation.

## Testing

Every SHALL requirement must have an automated test or a documented reason why
automation is not applicable. Run relevant tests after implementation and
report the results.

## Linter

Every implementation needs a validation of ruff using `ruff check . --fix`

## LLM Output

Structured output follows:

`LLM → parser → schema validation → retry → final failure`

Maximum 3 total attempts: 1 initial attempt + at most 2 retries.

Never silently accept malformed or incomplete output.

## Identity

Never infer student identity from prompt content.

Keep these identifiers separate:
- `student_id`
- `project_id`
- `exercise_id`
- `attempt_id`

## Evaluation

Standard `evaluate`:
- inspect the project read-only;
- require confirmation before Gradle execution;
- in non-interactive mode require explicit `--yes`;
- run build/compile, unit tests, Android Lint, and Detekt by default;
- never run `connectedAndroidTest` by default;
- treat missing evidence as a limitation, not success;
- never invent evidence.

Top-level rubric:
- functional requirements: 40%;
- tests: 20%;
- code quality: 15%;
- architecture: 15%;
- Android practices: 10%.

Per-exercise functional requirement subweights subdivide the fixed 40%
functional dimension and do not create additional global weight.

## Safety

Do not modify student source code during standard inspection, practice, ask,
or evaluation. Do not expose credentials or bypass execution policies.

## Change Discipline

If implementation reveals a genuine specification issue, update the relevant
specification and ADR before proceeding.

## Linting

At the end of every implementation task, run `ruff check . --fix` and report
the result.
