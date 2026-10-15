# ADA Sensei — 006 Evaluate Specification

## Objective

Evaluate an Android project against an exercise or structural evaluation criteria
and produce an evidence-based `EvaluationResult`.

The evaluation subsystem is also the reusable evidence and rubric infrastructure
for higher-level workflows such as `007-examine`.

## Core Principle

The LLM SHALL interpret collected evidence. It SHALL NOT be the sole source of
evidence and SHALL NOT invent evidence.

Evidence is collected by deterministic tools and associated with criteria before
LLM interpretation. Objective evidence SHALL be scored deterministically wherever
the rubric defines an objective rule.

## Scope

`006-evaluate` owns:

- Android project inspection;
- Gradle build/test execution;
- Android Lint and Detekt evidence collection;
- requirement-to-evidence matching;
- reusable evidence context;
- rubric mechanics and deterministic score computation;
- the default `/evaluate` rubric definition;
- structured LLM interpretation of evaluation evidence;
- `EvaluationResult` persistence;
- evaluation-specific attempt completion/history updates.

The reusable evaluation infrastructure MAY be consumed by other workflows.

`006-evaluate` does NOT own:

- examination lifecycle;
- exam timing;
- exam `/ask` counting;
- exam-specific documentation;
- exam-specific scoring dimensions;
- exam PDF report generation.

Those concerns belong to `007-examine`.

## Evaluation Engine Boundary

The implementation SHALL expose a reusable evaluation engine conceptually equivalent
to:

```text
EvaluationEngine
├── AndroidProjectAnalyzer
├── GradleTool
├── TestTool
├── StaticAnalysisTool
├── RequirementMatcher
├── EvidenceContextBuilder
├── RubricEngine
└── EvaluationAgent
```

`EvaluateAction` orchestrates the engine using the default evaluation rubric.

Other workflows MAY orchestrate the same engine with a different rubric definition
without duplicating evidence collection or Android analysis.

## Exercise Resolution

`/evaluate` evaluates against an exercise when available:

1. explicit `--exercise exercise://<uuid>`;
2. otherwise `SessionContext.current_exercise_id`;
3. otherwise structural evaluation only.

When no exercise exists, requirement-level scoring SHALL be skipped.

## Confirmation

Before any Gradle-based task, explicit confirmation is required.

Project inspection alone does not require confirmation.

In a non-interactive environment, Gradle execution SHALL require explicit `--yes`.

Declining confirmation SHALL prevent Gradle execution.

## Default Evidence Scope

The default `/evaluate` workflow executes:

1. project inspection;
2. Gradle build/compile;
3. unit tests;
4. Android Lint;
5. Detekt.

`connectedAndroidTest` SHALL NOT run by default.

The future `--instrumented` option remains outside the current implementation.

## Evidence Pipeline

```text
Student Project
      ↓
AndroidProjectAnalyzer
      ↓
EvaluationEngine
      ├── GradleTool
      ├── TestTool
      └── StaticAnalysisTool
      ↓
EvidenceContext
      ↓
RequirementMatcher
      ↓
RubricEngine + rubric definition
      ↓
EvaluationAgent
      ↓
Deterministic score computation
      ↓
EvaluationResult
      ↓
ResultStore
```

The LLM may provide qualitative interpretation, strengths, weaknesses,
recommendations, and explanations, but SHALL NOT replace deterministic evidence.

## Rubric Model

Rubric mechanics SHALL be reusable and separate from rubric definitions.

A `RubricDefinition` contains:

- stable rubric id;
- version;
- dimensions;
- weights;
- optional subcriteria;
- score scale;
- evidence sufficiency rules.

The default `/evaluate` rubric is:

| Dimension | Weight |
|---|---:|
| Functional requirements | 40% |
| Tests | 20% |
| Code quality | 15% |
| Architecture | 15% |
| Android practices | 10% |

These weights remain specific to `/evaluate`.

A future workflow such as `007-examine` MAY define another rubric without modifying
the default evaluate rubric.

## Scoring

Each evaluated dimension uses a 0–4 integer score.

| Score | Meaning |
|---|---|
| 4 | Excellent — fully satisfies the criterion with supporting evidence |
| 3 | Good — satisfies it with minor gaps |
| 2 | Partial — meaningful progress, clear gaps |
| 1 | Unsatisfactory — minimal or incorrect implementation |
| 0 | Unsupported — no indication of satisfaction |

The overall score is normalized to 0–100.

For exercise functional requirements, requirement subweights apply only within the
fixed 40% functional-requirements dimension.

```text
functional_dimension_score =
    Σ(functional_subweight_i × requirement_score_i)

overall =
    100 × Σ(top_level_weight[D] × dimension_score[D] / 4)
          / Σ(top_level_weight[D] for evaluated dimensions)
```

Top-level weights SHALL sum to 1.0.

Functional subweights SHALL sum to 1.0 when explicitly supplied.

Dimensions with insufficient evidence are `not_evaluated` and excluded from the
score denominator.

The LLM SHALL NOT override deterministic objective findings or the recomputed
overall score.

## Static Analysis

Android Lint and Detekt findings SHALL preserve:

- `ERROR`
- `WARNING`
- `INFO`

Findings are evidence. A finding SHALL NOT automatically become a one-to-one
grade deduction.

## Evidence Sufficiency

- Missing evidence SHALL NOT be interpreted as success.
- If build failure prevents meaningful requirement evaluation, affected criteria
  are `not_evaluated` and the build failure is reported as a blocking limitation.
- If tests cannot execute, the tests dimension is `not_evaluated` with a reason.
- If static analysis is unavailable, affected dimensions are `not_evaluated`.
- Tool failures SHALL be visible in the result.

## Structured LLM Output

Structured LLM responses SHALL follow:

```text
LLM
 ↓
structured parser
 ↓
schema validation
 ↓
retry if invalid
 ↓
final failure after 3 total attempts
```

Malformed or incomplete structured output SHALL never be silently accepted.

The LLM may interpret evidence but cannot invent evidence.

## Result Persistence

`EvaluationResult` SHALL be persisted using `ResultStore` as:

```text
result://<uuid>
```

The result SHALL preserve:

- `student_id`;
- `project_id`;
- `exercise_id` when available;
- `attempt_id`;
- rubric id/version;
- evidence;
- score;
- limitations;
- feedback.

A successful evaluation for a known attempt SHALL mark the attempt completed and
append the evaluation outcome to `HistoryStore`.

Persistence failures SHALL be explicitly reported.

## Safety

Standard evaluation SHALL NOT modify source code or student-owned project files.

Temporary build/test artifacts created by the normal Gradle toolchain are allowed.

Evaluation results are stored outside the student project.

## Reuse Contract for 007-examine

`007-examine` SHALL reuse the evaluation infrastructure for:

- Android project inspection;
- build evidence;
- unit-test evidence;
- Android Lint;
- Detekt;
- requirement matching;
- evidence context;
- deterministic rubric mechanics;
- structured LLM interpretation where applicable.

`007-examine` SHALL NOT modify the default `/evaluate` rubric.

`007-examine` owns its own exam lifecycle, exam rubric definition, exam metrics,
and exam report generation.
