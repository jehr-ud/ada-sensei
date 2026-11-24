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


## Mastery Evaluation Reuse

The reusable engine MAY be invoked by `008-learning-path` to evaluate stage exit
challenges. The caller supplies a versioned rubric definition and a set of stage
competencies/requirements; the engine returns evidence and criterion scores.
`006-evaluate` SHALL NOT decide whether the student advances a learning stage;
that decision belongs to `PlannerAgent` using the `ProgressionPolicy` in
`008-learning-path`. The `evaluate-default:v1` rubric remains unchanged.


## Agent Orchestration Contract

Every `/evaluate` request SHALL be orchestrated by `TeacherAgent` and include PlannerAgent, EvaluatorAgent, and TrainerAgent participation as specified by `009-agent-orchestration`. EvaluatorAgent owns evidence interpretation; PlannerAgent records evidence but does not advance the stage unless this is explicitly a mastery assessment; TrainerAgent explains findings and remediation. The existing default evaluation rubric and confirmation rules remain unchanged.


---

# Adenda normativa — Evaluación semántica asistida por LLM y evidencia trazable (v2)

**Estado:** propuesta de actualización. **Modelo objetivo:** `qwen2.5-coder:7b` mediante Ollama.

Esta adenda complementa y reemplaza únicamente las reglas incompatibles sobre la responsabilidad del LLM, la evidencia, el contrato del resultado y la interpretación de requisitos. Se conservan el límite reutilizable, la confirmación de Gradle, el alcance de herramientas, la persistencia y la política de no modificar el código del estudiante.

## A. Objetivo

`006-evaluate` debe producir un único `EvaluationResult` estructurado por ejecución. Cada decisión de cumplimiento debe poder rastrearse hasta evidencia real del proyecto. El LLM interpreta semánticamente el código y las pruebas; las fórmulas de puntuación siguen siendo deterministas.

## B. Responsabilidades

- `EvidenceCollector` / `AndroidProjectAnalyzer`: recopilan archivos, símbolos, rangos de líneas, imports, dependencias, resultados de build/tests y reportes de analizadores. No califican por sí solos.
- `LLMRequirementEvaluator`: evalúa cada criterio funcional y técnico suministrado por el caller, con base exclusiva en la evidencia recibida. Emite estado, explicación breve, evidencia citada y limitaciones.
- `LLMArchitectureEvaluator`: evalúa Clean Architecture y MVVM cuando la rúbrica del caller lo solicite.
- `RubricEngine` / `ScoreCalculator`: valida estados, aplica pesos y calcula las notas. No interpreta código.
- `EvaluationResult`: almacena la evaluación única, con versión de modelo, prompts, rúbrica, evidencias y cálculos.

El LLM SÍ puede decidir semánticamente `PASS`, `PARTIAL`, `FAIL` o `NOT_EVALUATED` para criterios funcionales y arquitectónicos. No puede crear evidencias, ejecutar comandos, alterar resultados de herramientas ni calcular o modificar la nota final.

## C. Modelo y reproducibilidad

Configuración por defecto: `provider=ollama`, `model_id=qwen2.5-coder:7b`, `temperature=0` (o mínimo soportado), salida JSON validada. Persistir `model_id`, digest si está disponible, versión del prompt, temperatura, fecha, duración, intentos y estado de validación. No sustituir silenciosamente el modelo. Si no está disponible o falla el esquema después de tres intentos, los criterios dependientes del LLM quedan `NOT_EVALUATED` con `LLM_UNAVAILABLE` o `LLM_INVALID_OUTPUT`; nunca reciben cero por fallo de infraestructura.

## D. Contrato de evidencia

Cada `EvidenceItem` debe incluir: `evidence_id`, `kind`, `artifact_path` relativo, `symbol` opcional, `line_start`/`line_end` cuando aplique, `excerpt` breve, `content_hash`, `collector`, herramienta/versión/comando cuando corresponda, `timestamp` y `reliability`. Las rutas y líneas deben existir en el snapshot inspeccionado. No se aceptan rutas absolutas ni referencias fabricadas.

Reglas de interpretación:

1. La presencia de una clase, carpeta, dependencia, comentario o nombre no demuestra comportamiento.
2. Un test solo acredita el escenario que ejecuta y verifica; no acredita automáticamente todo el requisito.
3. La documentación acredita lo declarado, no la implementación.
4. Una decisión `PASS`, `PARTIAL` o `FAIL` debe citar al menos una evidencia. `NOT_EVALUATED` debe incluir razón y limitación.
5. Separar hechos observados, inferencias del LLM y aspectos no verificables. Una inferencia nunca se presenta como hecho.

## E. Evaluación de criterios funcionales

El LLM evalúa cada `acceptance_criteria` del JSON, no solamente el requisito completo. La salida por criterio incluye `criterion_id`, `status`, `reason`, `evidence_ids`, `confidence`, `limitations` y `recommended_action`. El estado del requisito se deriva: todos los criterios evaluables PASS → PASS; mezcla de PASS y PARTIAL/FAIL → PARTIAL; evidencia directa de incumplimiento en todos los criterios relevantes → FAIL; evidencia insuficiente → NOT_EVALUATED. No se puede declarar PASS por inspección de nombres o por evidencia indirecta insuficiente.

Para autenticación, sincronización remota, navegación y comportamiento visual, la inspección estática puede demostrar integración o intención, pero no necesariamente el comportamiento en ejecución. Si no existe prueba runtime, test de integración o evidencia manual válida, declarar `PARTIAL` solo si el criterio admite una parte demostrada; en otro caso `NOT_EVALUATED`, explicando el límite.

## F. Estados comunes

`PASS`, `PARTIAL`, `FAIL`, `NOT_EVALUATED`, `NOT_CONFIGURED`, `NOT_AVAILABLE`, `EXECUTION_ERROR`, `INFO`. Los cuatro últimos estados técnicos no se convierten automáticamente en cero. `NOT_EVALUATED` se excluye del denominador y el reporte muestra el peso excluido.

## G. Contrato de salida

El resultado persistido debe ser una única instancia versionada `EvaluationResult` / `EvaluationReport`, con: identidad de intento; rubric id/version; modelo y prompt; dimensiones; criterios; evidencias; findings; limitaciones; desglose matemático; cobertura; estado global; fortalezas y acciones de mejora. El PDF y cualquier resumen de TUI consumen este objeto. No deben volver a evaluar ni construir una segunda nota.

## H. Validación

Antes de persistir, validar: todos los IDs de evidencia existen; los rangos de línea son válidos; cada decisión tiene evidencia o razón de no evaluación; pesos válidos; estados y puntuaciones compatibles; la nota recalculada coincide con el desglose; no hay criterios duplicados ni huérfanos. Si falla una validación, no emitir resultado oficial como completo.
