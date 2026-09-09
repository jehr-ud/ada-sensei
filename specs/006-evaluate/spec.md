# Evaluate Action Specification

## Objective

Evaluate a student's Android project against the requirements of an exercise and
provide evidence-based pedagogical feedback.

## Core Principle

The LLM SHALL interpret collected evidence. It SHALL NOT be the sole source of
evidence (ADR-003, RQ-EVA-007). Evidence is collected by deterministic tools and
associated with criteria before any interpretation. The LLM may interpret
evidence but SHALL NOT invent it.

## Exercise Resolution

`/evaluate` evaluates against an exercise when available:

1. explicit `--exercise exercise://<uuid>` (RQ-CLI-010);
2. else the session's current exercise (`SessionContext.current_exercise_id`);
3. else structural evaluation only: project inspection, static analysis, and
   unit tests — with no requirement-level scoring (RQ-EVA-006/017).

## Confirmation (ADR-016)

`/evaluate` SHALL prompt the user for confirmation before executing Gradle-based
tasks. Declining aborts the evaluation cleanly (RQ-CLI-014). Project inspection
alone does not require confirmation.

In a non-interactive environment, `evaluate` SHALL abort before Gradle execution
unless the explicit `--yes` confirmation override is supplied.

## Default Evaluation Scope (ADR-016)

The default evaluation runs, in order:

1. **Project inspection** — read-only structure and source analysis;
2. **Build (compile)** — `./gradlew` compile/assemble task;
3. **Unit tests** — `./gradlew test` / unit test reports;
4. **Android Lint** — `./gradlew lint`;
5. **Detekt** — `./gradlew detekt`.

`connectedAndroidTest` (instrumented tests) SHALL NOT run by default; it is
reserved for a future explicit `--instrumented` option (RQ-CLI-015).

## Evaluation Pipeline

```text
Student Project
      ↓
Project Analyzer            # read-only project structure
      ↓
[CONFIRM Gradle execution → approve]
      ↓
Build (./gradlew compile)
      ↓
Tests (./gradlew test)
      ↓
Static Analysis (Android Lint + detekt)
      ↓
Requirement Evidence        # RequirementMatcher: evidence ↔ req:// ids
      ↓
LLM Evaluation              # interprets evidence under the rubric
      ↓
EvaluationResult            # persisted via ResultStore (bound to attempt)
```

## Rubric and Scoring (ADR-017)

Five weighted dimensions (weights sum to 100%):

| Dimension | Weight | Evidence source |
|---|---|---|
| Functional requirements | 40% | requirement mapping, build/compile gate, source inspection, unit tests |
| Tests | 20% | unit test execution and reports |
| Code quality | 15% | detekt findings (ERROR/WARNING/INFO), code organization, error handling |
| Architecture | 15% | project structure, detekt, source-level LLM interpretation |
| Android practices | 10% | Android Lint findings (ERROR/WARNING/INFO) |

Functional-requirement criteria are driven by the exercise `evaluation_criteria`
when an exercise is present; otherwise the dimension is evaluated structurally.

Each evaluated dimension receives an integer score on a 0–4 scale:

| Score | Meaning |
|---|---|
| 4 | Excellent — fully satisfies the criterion with supporting evidence |
| 3 | Good — satisfies it with minor gaps |
| 2 | Partial — meaningful progress, clear gaps |
| 1 | Unsatisfactory — minimal or incorrect implementation |
| 0 | Unsupported — no indication of satisfaction |

Overall score SHALL be computed deterministically by the `Rubric`.

For each top-level dimension `D`, the dimension score is on a 0–4 scale. When
an exercise is present, functional requirement scores are first aggregated
using their normalized per-exercise subweights. Those subweights apply only
inside the fixed 40% functional-requirements dimension.

```text
functional_dimension_score =
    Σ(functional_subweight_i × requirement_score_i)

overall =
    100 × Σ(top_level_weight[D] × dimension_score[D] / 4)
          / Σ(top_level_weight[D] for evaluated dimensions)
```

The fixed top-level weights are:
`functional_requirements=0.40`, `tests=0.20`, `code_quality=0.15`,
`architecture=0.15`, `android_practices=0.10`.

Only evaluated top-level dimensions are included in the denominator. The rubric
MUST validate that top-level weights sum to 1.0 and that explicit functional
subweights sum to 1.0.

Dimensions marked **not evaluated** (no evidence) are excluded from the
numerator and denominator (ADR-011). If no dimension is evaluated, no overall
score is produced. Where objective evidence exists (tests, lint, detekt,
compile), scores SHALL be determined deterministically before LLM
interpretation; the LLM SHALL NOT override computed findings.

## Static Analysis Severity (ADR-012)

Android Lint and detekt findings carry `severity: ERROR | WARNING | INFO`.
Findings are **evidence**, and SHALL NOT automatically map one-to-one to grade
deductions; the rubric interprets them in aggregate with the LLM's pedagogical
judgement.

## Evidence Sufficiency (ADR-011 / RQ-EVA-012)

- A dimension without evidence is reported as **not evaluated**, never pass/fail.
- If the **build fails**, the functional-requirements dimension (and any
  compilation-dependent analysis) is marked not evaluated; the result reports
  the build as the blocking limitation and recommends fixing it first.
- If **tests** cannot run or do not exist, the tests dimension is marked not
  evaluated with the reason; absence of tests is not success.
- If **static analysis** cannot run (tool missing), affected dimensions are
  marked not evaluated with the reason (RQ-FND-019).
- The LLM SHALL fail cleanly (structured pipeline) rather than invent evidence.

## Feedback

The result SHALL include score, strengths, weaknesses, evidence,
recommendations, and a next learning activity. Feedback SHALL explain why an
issue matters and guide toward correction instead of merely grading
(RQ-EVA-008..010).

## Safety

Evaluation tools SHALL be read-only except for temporary build artifacts created
by the normal Android/Gradle toolchain (RQ-EVA-011). Evaluation results persist
via `ResultStore` (`result://<uuid>`) bound to the session attempt, never inside
the student project.
## Attempt completion and history

When an evaluation successfully completes for a known attempt, `EvaluateAction`
shall mark the attempt as `completed` and append the evaluation outcome to
`HistoryStore`.

```text
EvaluationResult
      ↓
ResultStore.write()
      ↓
AttemptStore.mark_completed()
      ↓
HistoryStore.append_evaluation()
```

All operations preserve `student_id`, `project_id`, `exercise_id`, and
`attempt_id`. Persistence failures are reported explicitly.
