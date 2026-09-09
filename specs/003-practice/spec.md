# Practice Action Specification

## Objective

Generate Android programming exercises adapted to the student's context, persist
them for later evaluation, and support progressive assistance.

## Core Behavior

`/practice` SHALL generate a solvable programming exercise instead of immediately
implementing the solution. The generated `Exercise` SHALL contain:

- title;
- topic;
- learning objective;
- difficulty;
- problem statement;
- functional requirements (each with a stable `req://<uuid>` id);
- constraints;
- expected deliverables;
- optional progressive hints;
- evaluation criteria mapped to the requirement ids.

## Inputs

```text
/practice
  --topic <topic>          # e.g. compose-state, viewmodel, kotlin-coroutines
  --difficulty <level>     # beginner | intermediate | advanced
  --objective <text>       # optional custom learning objective
  --adaptive / --no-adaptive
                           # adaptive default: ON when student history exists
```

When `--topic` or `--difficulty` is omitted, the system SHALL pick them from the
student profile when available, otherwise use sensible defaults and state them.

## Adaptation

When student history is available (`--adaptive`, default), the action SHALL
consider:

- previous exercises;
- success/failure;
- requested hints;
- recurring errors;
- known strengths and weaknesses.

## Practice → Evaluate Contract

- The generated `Exercise` SHALL be persisted through `ExerciseStore` and
  retrievable by its stable id (`exercise://<uuid>`) — foundation RQ-FND-012.
- Each functional requirement SHALL carry a stable `req://<uuid>` id.
- `evaluation_criteria` SHALL reference those `requirement_id`s so `/evaluate`
  can map evidence to requirements (ADR-009, RQ-PRA-010). For generated
  exercises, these criteria belong to the top-level
  `functional_requirements` dimension only; their weights are normalized
  subweights within that dimension and do not add global score weight.
- When the session has a current exercise, `/evaluate` uses it by default
  (RQ-CLI-010).
- Practice SHALL create an `Attempt` (`attempt://<uuid>`) binding `student_id`,
  `project_id`, and `exercise_id`, and record it as the session attempt
  (RQ-PRA-019). Student identity comes only from the session (ADR-015).

## Pedagogical Principle

The system SHALL not reveal a complete solution by default. The student may
request progressively stronger assistance via `/hint`, `/more`, and `/solution`
(see Progressive Assistance in 001-foundation, ADR-010).

## Example

```text
/practice --topic compose-state --difficulty intermediate

Exercise: "Task List with ViewModel State"
Objective: manage mutable UI state in a ViewModel using StateFlow.
Requirements:
  - R1: Add tasks.                (req://<uuid>)
  - R2: Remove tasks.             (req://<uuid>)
  - R3: Display tasks with LazyColumn.
  - R4: Keep UI state in a ViewModel.
Difficulty: Intermediate
```