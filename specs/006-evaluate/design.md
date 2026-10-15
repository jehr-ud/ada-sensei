# Design

## 1. Architecture

```text
                         EvaluationEngine
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
 AndroidProjectAnalyzer     EvidenceCollector     RequirementMatcher
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
               GradleTool      TestTool    StaticAnalysisTool
                    │             │             │
                    └─────────────┴─────────────┘
                                  │
                                  ▼
                           EvidenceContext
                                  │
                         ┌────────┴────────┐
                         │                 │
                         ▼                 ▼
                   RubricEngine     EvaluationAgent
                         │                 │
                         └────────┬────────┘
                                  ▼
                          EvaluationResult
                                  │
                              ResultStore
```

`EvaluateAction` is an orchestration layer over this engine. It owns the
`/evaluate` workflow, confirmation policy, exercise resolution, and persistence
integration. The reusable engine does not own CLI/TUI concerns.

## 2. Core Components

### EvaluationEngine

Conceptual interface:

```python
class EvaluationEngine:
    def collect_evidence(
        self,
        project: ProjectContext,
        exercise: Exercise | None,
        execution_policy: EvaluationExecutionPolicy,
    ) -> EvidenceContext:
        ...

    def evaluate(
        self,
        evidence: EvidenceContext,
        rubric: RubricDefinition,
        context: EvaluationContext,
    ) -> EvaluationResult:
        ...
```

The exact implementation language/API may follow the foundation conventions.

### AndroidProjectAnalyzer

Read-only inspection of:

- modules;
- source directories;
- Gradle configuration;
- manifests;
- Compose usage;
- architecture-relevant structure.

### GradleTool

Responsible for:

- wrapper discovery;
- build/compile;
- unit-test execution;
- command timeouts;
- subprocess result capture.

Default timeout remains 600 seconds unless overridden by foundation policy.

### TestTool

Collects unit-test reports and associates test evidence with requirements when
traceable.

It does not execute `connectedAndroidTest` by default.

### StaticAnalysisTool

Runs:

```text
./gradlew lint
./gradlew detekt
```

and parses findings into evidence records preserving:

```text
ERROR | WARNING | INFO
```

### RequirementMatcher

Maps evidence to `req://` requirement identifiers and records unmatched evidence.

It is independently callable by higher-level workflows.

### EvidenceContext

A workflow-neutral representation containing:

```text
project evidence
build evidence
test evidence
lint evidence
detekt evidence
structure evidence
requirement mappings
limitations
```

The context SHALL preserve provenance for each evidence item.

### RubricEngine

Contains scoring mechanics but not a hard-coded workflow rubric.

Conceptual input:

```text
RubricDefinition
+
CriterionScores
+
EvidenceStatus
```

Conceptual output:

```text
ScoreBreakdown
overall_score_0_100
evaluated_dimensions
not_evaluated_dimensions
```

### RubricDefinition

```text
RubricDefinition
├── id
├── version
├── dimensions[]
│   ├── id
│   ├── weight
│   └── subcriteria[]
├── score_scale
└── evidence_policy
```

The definition must validate:

- unique dimension ids;
- non-negative weights;
- top-level weight sum = 1.0;
- subcriteria weights = 1.0 when explicitly defined.

## 3. Default Evaluate Rubric

The default rubric is versioned independently:

```text
evaluate-default:v1
```

```text
functional_requirements = 0.40
tests                  = 0.20
code_quality           = 0.15
architecture           = 0.15
android_practices      = 0.10
```

`EvaluateAction` always resolves this rubric unless a future explicit evaluate
configuration mechanism is introduced.

Other workflows cannot mutate this definition.

## 4. Evidence Flow

```text
Project + Exercise + ExecutionPolicy
                │
                ▼
        EvaluationEngine
                │
        ┌───────┴────────┐
        ▼                ▼
  deterministic       requirement
     tools             matching
        │                │
        └───────┬────────┘
                ▼
         EvidenceContext
                │
                ▼
        EvaluationAgent
                │
                ▼
      structured interpretation
                │
                ▼
          schema validation
          /                   valid          invalid
         │              │
         │          retry (max 3 total)
         │              │
         └───────┬──────┘
                 ▼
          RubricEngine
                 │
                 ▼
      deterministic final score
```

The final score is computed from validated evidence and criterion scores. An LLM
overall score, if returned, is informational and SHALL NOT replace the computed
score.

## 5. Structured LLM Contract

The evaluation agent SHALL return a schema-conformant structure containing, at
minimum:

```text
dimension assessments
criterion assessments
evidence references
strengths
weaknesses
limitations
recommendations
next activity
```

Each claim about the project must reference available evidence where applicable.

Parsing behavior:

```text
attempt 1 → parse + validate
       ↓ invalid
attempt 2 → parse + validate
       ↓ invalid
attempt 3 → parse + validate
       ↓ invalid
explicit structured-output failure
```

No malformed result is accepted silently.

## 6. Confirmation Flow

```text
EvaluateAction
     │
     ├── project inspection
     │
     ├── needs Gradle?
     │
     └── confirmation
            │
        ┌───┴───┐
        no      yes
        │        │
      abort      ▼
              GradleTool
```

In non-interactive execution:

```text
--yes present → proceed
--yes absent  → abort before Gradle
```

## 7. Result Persistence

```text
EvaluationResult
      │
      ▼
ResultStore.write(result://uuid)
      │
      ├── AttemptStore.mark_completed(attempt_id)
      │
      └── HistoryStore.append_evaluation(...)
```

Persistence happens outside the student source tree.

Failures are explicit.

## 8. Reuse by 007-examine

The exam workflow should use:

```text
007-examine
     │
     ▼
EvaluationEngine
     ├── project inspection
     ├── Gradle/test evidence
     ├── Lint/Detekt evidence
     ├── RequirementMatcher
     └── RubricEngine
```

But it supplies its own:

```text
ExamRubricDefinition
ExamAttempt context
Exam metrics
Exam report generator
```

Therefore:

```text
/evaluate
    → EvaluateAction
    → EvaluationEngine
    → evaluate-default:v1

/exam-init
    → ExamineAction
    → EvaluationEngine
    → exam-default:v1
```

No action calls the other action internally.

## 9. Package Direction

Suggested implementation boundary:

```text
actions/evaluate.py
evaluation/
    engine.py
    evidence.py
    matcher.py
    rubric.py
    models.py
    agent.py
tools/
    gradle.py
    tests.py
    static_analysis.py
```

The exact package location may follow the final foundation package conventions.

The reusable evaluation package MUST NOT import CLI/TUI modules.

## 10. Testing Strategy

Test the reusable engine independently from `EvaluateAction`.

Required categories:

- evidence collection;
- requirement matching;
- rubric validation;
- deterministic scoring;
- structured output validation;
- retry limit;
- evidence provenance;
- evaluate rubric isolation;
- external workflow reuse;
- persistence;
- Gradle confirmation;
- build failure;
- missing-tool behavior.
