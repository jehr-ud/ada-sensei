# Design

## Components

```text
EvaluateAction
    │  (requires user confirmation before Gradle tasks)
    ├── AndroidProjectAnalyzer      # structure, modules, source files (read-only)
    ├── GradleTool                  # build + SubprocessRunner + discovery
    ├── TestTool                    # unit test reports collector
    ├── StaticAnalysisTool          # Android Lint + detekt (via wrapper)
    ├── RequirementMatcher          # evidence ↔ req:// ids (ExerciseStore)
    ├── Rubric                      # 5 dimensions, weights, 0–4 scale, deterministic score
    ├── ResultStore                 # persist result://<uuid> bound to attempt
    └── EvaluationAgent             # LLM structured interpretation
```

## Evidence Model (001-foundation)

```text
Evidence
- source: build | test | lint | detekt | file | llm
- type: compilation | unit_test | android_lint | detekt | structure | requirement
- severity: error | warning | info | null   # static-analysis findings
- status: pass | fail | skipped | missing
- message, file, line, command
```

## Execution Scope (ADR-016)

```text
inspect project            (no confirmation needed)
→ confirm Gradle execution (RQ-CLI-014)
→ ./gradlew compile/test    unit tests
→ ./gradlew lint            Android Lint
→ ./gradlew detekt          detekt
connectedAndroidTest NOT run (reserved: --instrumented)
```

## Evidence Flow

```text
Exercise (req:// ids, evaluation_criteria) + session attempt
        +
Project Evidence
        ↓
RequirementMatcher   # match evidence records to requirement ids
        ↓
Evaluation Context   # rubric + matched evidence, bounded by ContextManager
        ↓
LLM structured call  # schema for EvaluationResult (max 3 attempts)
        ↓
deterministic score computation (Rubric)   # overrides any LLM overall claim
        ↓
ResultStore.write(result://<uuid>)   # attempt_id + exercise_id bound
```

## Static Analysis Tooling (ADR-012)

- **detekt** → `./gradlew detekt`; parse report into Evidence records
  (`source=detekt`, `severity` from the finding: ERROR/WARNING/INFO).
- **Android Lint** → `./gradlew lint`; parse report into Evidence records
  (`source=lint`, `severity` from the finding).
- Both run through `GradleTool` with subprocess timeouts (default 600 s). If a
  task or tool is unavailable, `Evidence(status=missing)` + `ToolUnavailable`
  is emitted (RQ-FND-019), never silence.
- Findings feed the rubric as evidence; they are not automatically converted
  into grade deductions (ADR-012 / RQ-EVA-015).

## Requirement Matching

Given an exercise, `evaluation_criteria` provide `requirement_id`, `dimension`,
and normalized `weight` subweights. For generated exercises, these criteria
belong to the `functional_requirements` dimension and their subweights sum to
1.0. The matcher attaches:
- build/compile success → functional-requirements dimension (where mapping is
  explicit via requirement ids or file paths);
- passed/failed unit tests referencing requirement ids or test names → tests +
  functional mapping when explicit;
- lint/detekt findings with file/line and severity → Android practices / code
  quality dimensions;
- structural findings → architecture / code quality.

Unmatched evidence is still recorded in the result.

## Rubric and Scoring (ADR-017)

```text
Top-level dimensions:
  functional_requirements  0.40
  tests                    0.20
  code_quality             0.15
  architecture             0.15
  android_practices        0.10
```

For an exercise, functional `evaluation_criteria` use normalized subweights
within the fixed functional dimension. Their subweights must sum to 1.0.
Therefore the functional dimension contributes at most 40% to the final score.

```text
functional_dimension_score =
    Σ(functional_subweight_i × requirement_score_i)

overall =
    100 × Σ(top_level_weight_D × dimension_score_D / 4)
          / Σ(top_level_weight_D for evaluated dimensions)
```

The rubric validates that top-level weights sum to 1.0 and functional
subweights sum to 1.0 when explicitly supplied. Invalid configurations are
rejected. Functional subweights never add extra global score weight.

Deterministic evidence is scored before LLM interpretation. The LLM may provide
qualitative interpretation but cannot change deterministic evidence or the
recomputed overall score.

## Result Persistence

`EvaluationResult` is written via `ResultStore` (`result://<uuid>`) and is bound
to the session `attempt_id` (and `exercise_id` when present). After successful
evaluation, `AttemptStore.mark_completed(attempt_id)` marks the attempt
completed and `HistoryStore.append_evaluation(...)` records the outcome for
future learning recommendations. Persistence failures are explicit.

## Safety

Write operations are limited to temporary build/test artifacts inside the
project (`build/`, `.gradle/`) created only after user confirmation, plus the
`ResultStore` data directory. Source files are never modified.
## Non-interactive confirmation

In non-interactive execution, Gradle tasks require the explicit `--yes`
confirmation override; otherwise evaluation aborts before Gradle execution.
