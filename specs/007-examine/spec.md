# Examine Action Specification

## Objective

`exam-init` is a supervised exam-assessment workflow for an Android project. It
reuses the deterministic evidence collection and scoring infrastructure from
`006-evaluate`, but adds an exam lifecycle, exam-specific process evidence, and
a detailed PDF assessment report.

The resulting grade is a **suggested grade from 1.0 to 5.0**, with a raw
assessment score from 0 to 50. The system MUST expose both values:

- `raw_score`: integer 0–50
- `suggested_grade`: decimal 1.0–5.0

The suggested grade is derived deterministically from the raw score:

`grade = round(1.0 + (raw_score / 50.0) * 4.0, 1)`

The exam engine MUST NOT silently replace missing evidence with assumptions.

## Relationship with `006-evaluate`

`exam-init` SHALL reuse the `006-evaluate` evaluation engine boundary:

- `EvaluationEngine`
- `EvidenceContext`
- `AndroidProjectAnalyzer`
- `GradleTool`
- `TestTool`
- `StaticAnalysisTool`
- `RequirementMatcher`
- `RubricEngine`
- `RubricDefinition`
- structured LLM evaluation pipeline
- `ResultStore`
- `AttemptStore`
- `HistoryStore`

Per ADR-022, `exam-init` orchestrates `EvaluationEngine` directly; it SHALL NOT call
`EvaluateAction`. Per ADR-023, rubric mechanics come from the shared `RubricEngine`
while the exam supplies its own versioned `RubricDefinition` (`exam-default:v1`).
`exam-init` SHALL NOT read, mutate, or substitute `evaluate-default:v1`.

`exam-init` / `exam-finish` is an orchestration layer and an exam-specific rubric configuration,
not a second implementation of project evaluation.

The normal `evaluate` action remains available for ordinary exercise/project
evaluation. `exam-init` / `exam-finish` adds exam lifecycle and process evidence.

## Exam lifecycle

```text
START EXAM
    ↓
Resolve ExamDefinition
    ↓
Validate Android project
    ↓
Create ExamAttempt
    ↓
Create docs/ada-sensei/
    ↓
Record start timestamp
    ↓
Student works
    ├── /ask usage is counted
    ├── project changes are made by student
    └── exam documentation may be supplied
    ↓
FINISH EXAM
    ↓
Record end timestamp
    ↓
Collect project evidence
    ↓
Collect exam documentation evidence
    ↓
Run Evaluate evidence pipeline
    ↓
Calculate deterministic rubric
    ↓
Generate detailed PDF
    ↓
Persist ExamResult
    ↓
Mark attempt completed
```

## Exam definition and documentation

An exam MUST have an authoritative exam definition. Supported sources:

1. Markdown/text specification supplied by the instructor;
2. a structured exam specification;
3. an instructor-provided PDF statement.

The source is evidence/context for the exam requirements. If a PDF is supplied,
the original file SHALL be preserved and the extracted/normalized requirements
MUST be reviewable.

The student may document the implementation using:

- `docs/` Markdown/spec files;
- diagrams or text documentation;
- an instructor-defined documentation template;
- other files explicitly accepted by the exam definition.

The system MUST distinguish:

- `exam_statement` — instructor-provided requirements;
- `student_documentation` — student's explanation/design evidence;
- `project_evidence` — evidence collected from the Android project;
- `process_evidence` — duration and `/ask` usage.

The LLM may interpret documentation, but documentation alone cannot assert that
functionality works when objective project evidence contradicts it.

## Project docs directory

When an exam starts, ADA Sensei SHALL create:

```text
docs/
└── ada-sensei/
    └── exams/
        └── <exam_id>/
            ├── exam-context.md
            ├── exam-rubric.md
            └── README.md
```

These files explain the active exam context, rubric, and expected documentation
format. They MUST NOT contain the final grade.

After the exam finishes, ADA Sensei SHALL add:

```text
docs/
└── ada-sensei/
    └── exams/
        └── <exam_id>/
            ├── exam-context.md
            ├── exam-rubric.md
            ├── README.md
            ├── architecture.md
            └── evaluation-summary.md
```

The final PDF SHALL be written to the ADA Sensei data/output location, not into
the student's source tree, unless the user explicitly requests a project copy.

## Start exam

The action SHALL support:

```text
exam-init
```

or the equivalent direct CLI command (`/exam-init` in the TUI).

Starting an exam requires confirmation.

At start:

1. resolve `student_id`;
2. resolve `project_id`;
3. resolve `exam_id`;
4. create a new `exam_attempt_id`;
5. record `started_at`;
6. initialize `ask_count = 0`;
7. initialize event history;
8. create the exam docs directory;
9. show the exam rules and allowed assistance policy.

Student identity MUST come from explicit `--student <student_id>` or the
established session identity mechanism. It MUST NOT be inferred from the prompt.

## Exam identity

The system MUST keep these identifiers separate:

- `student_id`
- `project_id`
- `exam_id`
- `exercise_id` (optional)
- `attempt_id`
- `exam_attempt_id`

`exam_attempt_id` identifies one execution of one exam by one student.

## Ask tracking

Every successful invocation of the `ask` action during an active exam MUST
increment:

`exam_attempt.ask_count`

The system SHALL also persist an event:

```text
AskEvent
- timestamp
- action = ask
- question_id
- duration_ms
```

Failed/cancelled requests SHALL be recorded separately but MUST NOT count as a
successful answered `/ask` unless the exam definition explicitly says otherwise.

The count MUST be based on application events, not terminal text parsing.

## Duration tracking

The system SHALL record:

- `started_at`
- `finished_at`
- `duration_seconds`

If the exam defines a maximum duration, the system SHALL also record:

- `allowed_duration_seconds`
- `overtime_seconds`

The timer starts when the exam is started and ends when the student selects
Finish Exam and confirmation completes.

The system MUST NOT rely on terminal timestamps or LLM claims for duration.

## Exam finish

The student explicitly selects:

```text
exam-finish
```

or `/exam-finish` in the TUI.

The system SHALL:

1. request confirmation;
2. stop the exam timer;
3. prevent further `/ask` usage for that exam attempt;
4. collect final project evidence;
5. collect student documentation;
6. run the evaluation pipeline;
7. generate the final assessment;
8. persist the result.

After finishing, the attempt is immutable except for administrative metadata.

## Evaluation scope

Exam evaluation SHALL reuse the default evaluation evidence:

1. project inspection;
2. build/compile;
3. unit tests;
4. Android Lint;
5. Detekt.

`connectedAndroidTest` SHALL NOT run by default.

If an exam explicitly enables instrumented tests, the current system MUST still
reject them until the future instrumented-test capability is implemented.

Gradle execution SHALL use the existing confirmation policy from `006-evaluate`.

## Exam rubric

The initial exam rubric is the versioned `RubricDefinition` `exam-default:v1`:

| Dimension | Weight |
|---|---:|
| Functional requirements | 40% |
| Tests | 15% |
| Code quality | 15% |
| Clean architecture | 15% |
| Android practices | 5% |
| Exam process | 10% |

Exam process is subdivided:

| Criterion | Weight inside exam process |
|---|---:|
| Duration | 50% |
| `/ask` usage | 50% |

Therefore:

- duration contributes 5% of the total;
- `/ask` usage contributes 5% of the total.

The weights MUST sum to 100%.

## Functional requirements

Functional requirements are derived from the authoritative exam definition.

Each functional requirement SHALL have:

- stable requirement id;
- description;
- evidence expectations;
- optional weight.

Functional subweights MUST sum to 1.0.

The functional dimension contributes 40% of the total exam score.

The LLM may explain whether evidence supports a requirement, but the final
functional score is recomputed deterministically from evidence and the rubric.

## Tests

The tests dimension uses:

- executed unit-test results;
- test reports;
- test existence;
- requirement/test mapping where available.

If tests cannot execute, the dimension is `not_evaluated` rather than silently
passing.

## Code quality

Evidence includes:

- Detekt;
- source structure;
- duplication/complexity where deterministic tooling exposes it;
- error handling;
- readability;
- maintainability.

Lint/Detekt findings are evidence, not automatic one-to-one deductions.

## Clean architecture

The architecture dimension evaluates:

- separation of presentation/domain/data responsibilities;
- dependency direction;
- appropriate abstraction boundaries;
- state management;
- testability;
- avoidance of inappropriate coupling.

Evidence sources include project structure, source inspection, dependency
configuration, and explicitly provided student architecture documentation.

The LLM may interpret architectural evidence but SHALL NOT invent components or
relationships not present in the project.

## Android practices

Evidence includes Android Lint plus project inspection for:

- lifecycle-aware behavior;
- Compose practices;
- resource usage;
- Android API usage;
- configuration-sensitive behavior;
- other practices represented by deterministic evidence.

## Exam process scoring

### Duration

If the exam specifies an allowed duration, duration is scored deterministically
using the following initial bands:

- within 100% of allowed time: 4
- >100% and <=110%: 3
- >110% and <=125%: 2
- >125% and <=150%: 1
- >150%: 0

If no duration limit is defined, duration is reported but the duration criterion is
`not_evaluated` and excluded from the denominator.

### `/ask` usage

The exam definition SHOULD specify an allowed ask count.

Initial bands:

- <= 50% of allowed asks: 4
- >50% and <=100%: 3
- >100% and <=150%: 2
- >150% and <=200%: 1
- >200%: 0

The exam definition may override these bands.

If no ask limit is defined, ask usage is reported but the criterion is
`not_evaluated` and excluded from the denominator.

Ask usage measures use of the tutor, not correctness. It MUST NOT be used to
claim academic dishonesty or intent.

## Deterministic scoring

Each evaluated criterion receives a 0–4 integer score.

The exam raw score is:

```text
raw_score_50 =
    50 ×
    Σ(weight_dimension × dimension_score / 4)
    / Σ(weight_dimension for evaluated dimensions)
```

The raw score SHALL be rounded to the nearest integer in [0, 50].

The suggested grade is:

```text
suggested_grade =
    round(1.0 + (raw_score_50 / 50.0) * 4.0, 1)
```

Therefore:

- 0 → 1.0
- 25 → 3.0
- 50 → 5.0

The report MUST display both values.

Missing evidence never becomes success. Dimensions or criteria without evidence
are marked `not_evaluated` and excluded from the denominator.

## Suggested grade status

The result MUST be explicitly labeled:

> Suggested grade — generated by ADA Sensei

It is an assessment aid for the instructor, not an authoritative institutional
grade.

The PDF MUST show the evidence and calculation behind the suggested grade.

## Architecture explanation

The final evaluation SHALL contain an architecture section describing the
current Android project's actual architecture.

It should identify, where present:

- modules;
- packages;
- UI layer;
- domain layer;
- data layer;
- repositories;
- ViewModels;
- dependency injection;
- navigation;
- persistence;
- network/API boundaries;
- testing structure.

It MUST distinguish:

- observed architecture;
- student-documented architecture;
- inferred interpretation.

The LLM MUST NOT present unsupported architecture as fact.

## PDF report

The generated PDF SHALL contain:

1. exam identification;
2. student;
3. project;
4. exam attempt id;
5. start/end timestamps;
6. duration;
7. ask count;
8. allowed ask count when defined;
9. rubric;
10. functional requirements and evidence;
11. test results;
12. code-quality findings;
13. architecture explanation;
14. Android-practice findings;
15. exam-process metrics;
16. strengths;
17. weaknesses;
18. recommendations;
19. detailed evidence;
20. raw score 0–50;
21. suggested grade 1.0–5.0;
22. limitations/not-evaluated criteria;
23. methodology and calculation.

The PDF MUST NOT contain unsupported claims.

## Structured LLM output

The LLM output SHALL be schema validated using the shared structured-output
pipeline:

LLM
→ parser
→ schema validation
→ retry
→ final failure

Maximum 3 total attempts.

Malformed or incomplete output MUST NOT be silently accepted.

## Persistence

The result SHALL be persisted with:

- `student_id`
- `project_id`
- `exam_id`
- `exam_attempt_id`
- optional `exercise_id`
- `attempt_id`
- timestamps
- ask count
- duration
- rubric version
- raw score
- suggested grade
- evidence references
- report path/id

After successful completion:

```text
ExamResult
    ↓
ResultStore
    ↓
AttemptStore.mark_completed()
    ↓
HistoryStore.append_exam_result()
```

Persistence failures MUST be explicit.

## Security and integrity

ADA Sensei MUST NOT modify student source files as part of evaluation.

Generated exam documentation and report metadata must be clearly identified as
ADA Sensei generated content.

The exam timer and ask count MUST come from application events and persisted
state, not from model-generated text.

## Out of scope

- automatic plagiarism detection;
- automatic cheating accusations;
- emotion/behavior inference;
- webcam/screen monitoring;
- hidden surveillance;
- automatic institutional grade submission;
- connectedAndroidTest execution before the future instrumented-test feature.
