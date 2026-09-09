# Design

## Components

```text
PracticeAction
  ├── PracticeInput        # topic?, difficulty?, objective?, adaptive?
  ├── StudentContext       # from HistoryStore (foundation RQ-FND-011)
  ├── ExerciseSpecification
  ├── PracticePrompt       # includes schema for structured output
  ├── LLMClient            # structured pipeline (001-foundation)
  ├── ExerciseStore        # persist exercise://<uuid>
  └── PracticeResult
```

## Flow

```text
CLI flags
   ↓
Input (topic/difficulty/objective/adaptive)
   ↓
validate; resolve defaults from StudentContext (adaptive)
   ↓
ExerciseSpecification -> PracticePrompt
   ↓
LLM structured call
   ↓
Exercise validation (Pydantic + JSON Schema, max 3 tries)
   ↓
ExerciseStore.write(exercise://<uuid>)
   ↓
AttemptStore.write(attempt://<uuid>)   # student_id + project_id + exercise_id
   ↓
SessionContext.attempt_id = attempt.id
SessionContext.current_exercise_id = exercise.id
   ↓
PracticeResult (rendered by CLI formatter)
```

Attempt identity: the action SHALL NOT infer the student; it reads
`SessionContext.student_id` set by the name received at session start
(ADR-015). `project_id` is derived from the active project path (RQ-FND-022).

## Input Model

```text
PracticeInput
- topic: str | None
- difficulty: Difficulty | None
- objective: str | None
- adaptive: bool          # default True when history exists else True anyway
```

Unknown topic strings are normalized against the knowledge taxonomy
(`knowledge/` in 005-examples); difficulty is strictly one of
beginner|intermediate|advanced — invalid values are rejected with a clear error.

## Exercise Model

```text
Exercise
- id: exercise://<uuid>
- title, topic, difficulty, objective, statement
- requirements: [Requirement]      # requirement.id: req://<uuid>
- constraints: [str]
- hints: [str]                     # progressive, ordered
- evaluation_criteria: [Criterion] # {requirement_id, dimension=functional_requirements, weight=subweight}
- source: generated
- created_at
```

Adaptive generation: the prompt includes the student-history summary when
`adaptive=True` and history exists; otherwise the action generates with explicit
"no history available" context (adaptive selection of defaults).

## Progressive Assistance

- `/hint`   → next element of `exercise.hints` for the current exercise.
- `/more`   → next `AssistanceLevel` for the current exercise (handled by the
  same LLM session, levels maintained in `SessionContext`, RQ-FND-016).
- `/solution` → jump directly to `AssistanceLevel.solution`.

## Persistence

Only `ExerciseStore` writes occur (outside the student project). The student
project is never modified by Practice.

## Traceability

- RQ-PRA-001..006: PracticeAction + StudentContext + prompt.
- RQ-PRA-007..009: prompt + assistance levels; RQ-PRA-010: ExerciseStore + Criterion.