# Design — Examine Action

## Architectural position

`exam-init` / `exam-finish` is an orchestration layer over `006-evaluate`.

```text
                          ┌──────────────────┐
                          │   ExamineAction  │
                          └────────┬─────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
        ExamLifecycle        ExamEvaluation        ExamRubric
              │                    │                    │
       start/finish      006-evaluate engine       process metrics
       ask counter       (same instance of         duration/ask
       duration          EvaluationEngine)
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   ▼
                            ExamScoring
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
              RubricEngine +             EvaluationAgent
              exam-default:v1                    │
                     └─────────────┬─────────────┘
                                   ▼
                              ExamResult
                                   │
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
                 ResultStore   HistoryStore     PDF
```


## Core models

### ExamDefinition

```text
exam_id
title
version
statement_source
requirements[]
allowed_duration_seconds?
allowed_ask_count?
rubric_ref          # defaults to "exam-default:v1"
documentation_rules
```

### ExamRequirement

```text
requirement_id
description
dimension
weight
evidence_expectations[]
```

### ExamAttempt

```text
exam_attempt_id
student_id
project_id
exam_id
exercise_id?
attempt_id
started_at
finished_at?
duration_seconds?
allowed_duration_seconds?
overtime_seconds?
ask_count
status
event_ids[]
```

### ExamEvent

```text
event_id
exam_attempt_id
type
timestamp
metadata
```

Event types initially:

```text
EXAM_STARTED
ASK_STARTED
ASK_COMPLETED
ASK_FAILED
ASK_CANCELLED
EXAM_FINISH_REQUESTED
EXAM_FINISHED
EVALUATION_STARTED
EVALUATION_COMPLETED
```

### ExamResult

```text
exam_attempt_id
rubric_version
dimensions[]
functional_requirements[]
process_metrics
architecture_report
strengths[]
weaknesses[]
recommendations[]
evidence[]
limitations[]
raw_score_50
suggested_grade
report_id/path
```

## Exam lifecycle state machine

```text
CREATED
  ↓
ACTIVE
  ├── ASK_STARTED → ASK_COMPLETED
  ├── ASK_STARTED → ASK_FAILED
  ├── ASK_STARTED → ASK_CANCELLED
  │
  └── FINISH_REQUESTED
          ↓ confirmation
      EVALUATING
          ↓
      COMPLETED
```

A completed attempt cannot accept new ask events.

## `/ask` integration

Do not modify AskAction's pedagogical behavior.

Instead, emit an application event when AskAction starts/completes.

```text
AskAction
   ↓
ExamSessionTracker.record_ask_event(...)
```

This keeps the exam counter independent from the TUI and direct CLI.

## Documentation

At exam start:

```text
docs/
└── ada-sensei/
    └── exams/
        └── <exam_id>/
            ├── README.md
            ├── exam-context.md
            └── exam-rubric.md
```

`exam-context.md` contains the normalized instructor exam requirements.

Student-authored documentation should remain distinguishable, for example:

```text
docs/
├── exam/
│   ├── requirements.md
│   ├── architecture.md
│   └── submission.md
└── ada-sensei/
    └── exams/
        └── <exam_id>/
            ...
```

The system must not overwrite student-authored files.

## PDF generation

Use a dedicated `ExamReportGenerator`.

Input:

```text
ExamResult
```

Output:

```text
PDF
```

Recommended report structure:

1. Cover
2. Exam metadata
3. Executive assessment
4. Rubric and calculation
5. Functional requirements
6. Test evidence
7. Code quality
8. Clean architecture
9. Android practices
10. Exam process
11. Architecture map
12. Strengths
13. Weaknesses
14. Recommendations
15. Detailed evidence
16. Limitations
17. Suggested grade

## Rubric engine

Reuse the deterministic `RubricEngine` from `006-evaluate` and supply the exam's
own versioned `RubricDefinition` (`exam-default:v1`). Per ADR-023 the exam SHALL
NOT instantiate or mutate `evaluate-default:v1`.

```text
functional_requirements  0.40
tests                    0.15
code_quality             0.15
clean_architecture      0.15
android_practices        0.05
exam_process             0.10
```

`exam_process`:

```text
duration   0.50
ask_usage  0.50
```

Thus:

```text
duration   = 0.05 global
ask_usage  = 0.05 global
```

The rubric supports `not_evaluated` criteria and renormalizes the denominator
exactly as `006-evaluate`.

## Duration scorer

If `allowed_duration_seconds` is present:

```text
ratio = actual_duration / allowed_duration

ratio <= 1.00  → 4
ratio <= 1.10  → 3
ratio <= 1.25  → 2
ratio <= 1.50  → 1
otherwise      → 0
```

If no allowed duration exists:

```text
criterion = NOT_EVALUATED
```

## Ask usage scorer

If `allowed_ask_count` is present:

```text
ratio = ask_count / allowed_ask_count

ratio <= 0.50  → 4
ratio <= 1.00  → 3
ratio <= 1.50  → 2
ratio <= 2.00  → 1
otherwise      → 0
```

If no ask limit exists:

```text
criterion = NOT_EVALUATED
```

These defaults should be versioned in the exam rubric and can be overridden by
an instructor-defined rubric.

## Evidence policy

The LLM receives:

- exam requirements;
- matched evidence;
- student documentation;
- architecture evidence;
- process metrics;
- rubric instructions.

The LLM returns structured qualitative interpretation only.

The deterministic rubric computes:

- dimension scores;
- raw 0–50 score;
- suggested 1.0–5.0 grade.

The LLM cannot override these values.

## PDF integrity

The PDF must include a calculation table so an instructor can reconstruct the
suggested grade.

Example:

```text
Dimension                 Weight   Score  Contribution
Functional requirements    40%      3.5       35.0
Tests                      15%      3.0       11.25
Code quality               15%      3.5       13.125
Clean architecture        15%      3.0       11.25
Android practices           5%      4.0        5.0
Exam process               10%      3.0        7.5
-------------------------------------------------------
Raw score                              83.125 / 100
Converted                                  41.6 / 50
Suggested grade                              4.3 / 5.0
```

The exact values in generated reports come from the actual rubric calculation;
this table is illustrative only.

## Security/integrity

No source modifications are permitted.

Generated files are limited to:

- `docs/ada-sensei/...` documentation;
- temporary Gradle/build artifacts;
- ADA Sensei data/output storage.

The exam attempt log is authoritative for duration and ask count.
