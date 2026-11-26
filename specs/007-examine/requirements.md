# Requisitos — 007 Examine

## RQ-EXM-001 — Identidad del examen
Se conservan separados `student_id`, `project_id`, `exam_id`, `attempt_id` y
`exam_attempt_id`. Ningún identificador se infiere del contenido del enunciado.

## RQ-EXM-002 — Definición autoritativa con dos formatos Markdown
El examen se carga desde un archivo suministrado por el docente. `ExamDefinitionLoader`
es el único responsable de interpretar y normalizar el enunciado; preserva el
texto original y la ruta fuente.

Se admiten tres fuentes: Markdown (`.md`), JSON estructurado y PDF.

Para Markdown, el loader reconoce dos formatos explícitos:

**Formato A — lista de bullets** bajo un encabezado que coincida con
`_REQUIREMENT_HEADINGS` (p.ej. `## Requirements`, `## Requisitos`).

**Formato B — tabla Markdown** bajo un encabezado que coincida con
`_CRITERIA_HEADINGS`, incluyendo encabezados numerados (p.ej.
`## 7. Criterios de evaluación`). La tabla debe tener columna `ID` y columna
de descripción. La columna de peso se detecta por prioridad: `Peso funcional`
tiene precedencia sobre `Puntaje`.

Si el formato no puede interpretarse, se agrega una limitación explícita con la
sección y el motivo. Nunca se declara silenciosamente que no hay requisitos.

## RQ-EXM-003 — Inicio transaccional
El sistema solo crea y persiste `ExamAttempt`, definición, eventos de inicio y
documentación después de que el estudiante confirme explícitamente el inicio y
todas las precondiciones hayan pasado. La operación crea exactamente un intento.

## RQ-EXM-004 — Finalización
El sistema preserva el flujo de finalización y la inmutabilidad del intento
completado. `ExamAttemptImmutableError` se lanza si se intenta modificar un
intento completado fuera de `ADMINISTRATIVE_FIELDS`.

## RQ-EXM-005 — Conteo de consultas
El sistema cuenta `/ask` exitosos mediante eventos `ASK_COMPLETED`; no usa
texto de terminal ni salida del LLM.

## RQ-EXM-006 — Historial de eventos
El sistema persiste eventos de examen con `event_id`, `exam_attempt_id`, tipo,
timestamp, `question_id`, `duration_ms` y `metadata`.

## RQ-EXM-007 — Duración autoritativa
El sistema calcula la duración desde timestamps persistidos (`started_at`,
`finished_at`). El reloj de pantalla es solo presentación y nunca constituye
evidencia ni fuente de verdad.

## RQ-EXM-008 — Documentación del estudiante con globs ampliados
`DocumentationRules` define qué archivos del proyecto cuentan como documentación.
Los globs predeterminados cubren:

```
docs/exam/**/*.md, docs/exam/**/*.txt,
docs/**/*.md, docs/**/*.txt, docs/**/*.pdf,
*.md, INFORME*.md, REPORT*.md, informe*.md, report*.md
```

Los globs son configurables por el docente desde el enunciado con
`documentation_rules.accepted_globs`. Deben distinguirse:

- Documento no encontrado.
- Documento encontrado.
- Documento encontrado pero ilegible.
- Documento sin contenido relevante.

## RQ-EXM-009 — Documentación generada
Al iniciar se crea `docs/ada-sensei/exams/<exam_id>/` con `README.md`,
`exam-context.md` y `exam-rubric.md`, sin sobrescribir archivos del estudiante
que no tengan el marcador generado por ADA Sensei (`<!-- ADA Sensei generated -->`).

## RQ-EXM-010 — Evidencia del proyecto
Se reutiliza el pipeline de `006-evaluate` para inspección, build, pruebas
unitarias, Android Lint y Detekt. El código fuente del estudiante no se modifica.

## RQ-EXM-011 — Sin pruebas instrumentadas
No se ejecuta `connectedAndroidTest`. `--instrumented` continúa siendo rechazado
con `InstrumentedNotSupportedError`.

## RQ-EXM-012 — Requisitos funcionales
Los ids de requisito son estables (derivados del texto del enunciado), los pesos
funcionales deben sumar exactamente 1.0, y cada requisito se asocia a evidencias
reales del proyecto.

## RQ-EXM-013 — Calidad de código
Se evalúa determinísticamente desde evidencias de Detekt. La interpretación LLM
es acotada (solo narrativa, nunca modifica puntuaciones).

## RQ-EXM-014 — Arquitectura limpia
La puntuación de `clean_architecture` se basa exclusivamente en señales
observadas en la estructura del proyecto. Las afirmaciones documentadas e
inferidas no pueden incrementar la puntuación.

## RQ-EXM-015 — Pruebas
Las pruebas unitarias no disponibles se reportan como `not_evaluated`, nunca
como éxito supuesto.

## RQ-EXM-016 — Prácticas Android
Se evalúa determinísticamente desde evidencias de Android Lint.

## RQ-EXM-017 — Rúbrica de proceso
Duración y uso de `/ask` se evalúan solo si el enunciado establece
`allowed_duration_seconds` o `allowed_ask_count`. Sin límites, ambas subcriteria
se marcan `not_evaluated (no_limit)`. Los pesos de las subcriteria se leen
desde la rúbrica versionada, no hardcodeados.

## RQ-EXM-018 — Pesos de examen
La rúbrica `exam-default:v1` usa: `functional_requirements` 40%, `tests` 15%,
`code_quality` 15%, `clean_architecture` 15%, `android_practices` 5%,
`exam_process` 10%.

## RQ-EXM-019 — Puntaje determinista
El puntaje se calcula a partir de dimensiones evaluadas; denominador cero produce
`not_evaluated` en lugar de un puntaje ficticio.

## RQ-EXM-020 — Rango del puntaje
El puntaje bruto `raw_score_50` se mantiene en el rango 0–50.

## RQ-EXM-021 — Nota sugerida
La nota sugerida se deriva determinísticamente:
`grade = round(1.0 + (raw_score_50 / 50.0) * 4.0, 1)`.

## RQ-EXM-022 — Suficiencia de evidencia
La ausencia de evidencia nunca se interpreta como cumplimiento de un requisito.

## RQ-EXM-023 — Informe de arquitectura
El informe de arquitectura separa afirmaciones observadas, documentadas e
inferidas. Las inferencias del LLM se aceptan solo cuando citan referencias de
evidencia reales (`ev://` o `doc://`).

## RQ-EXM-024 — Informe PDF en el proyecto
El informe PDF se escribe en `docs/ada-sensei/exams/<exam_id>/report.pdf` dentro
del árbol del proyecto examinado. No se escribe en el directorio de datos de ADA
Sensei.

## RQ-EXM-025 — Salida estructurada con normalización
Las respuestas estructuradas del LLM siguen el pipeline compartido (máximo 3
intentos). Una respuesta que devuelva un **objeto** donde el esquema espera un
**array** se normaliza automáticamente envolviéndola en una lista antes de
validar el esquema, sin consumir un intento de reintento. Un objeto de decisión
solitario también se envuelve en el array batch correspondiente antes de
validar.

## RQ-EXM-026 — Persistencia
Los fallos de persistencia (`ResultStore`, `AttemptStore`, `HistoryStore`) se
reportan como limitaciones en el resultado, no se silencian.

## RQ-EXM-027 — Historial
El resultado final se agrega al historial del estudiante.

## RQ-EXM-028 — Integridad del proyecto
La evaluación no modifica archivos fuente del estudiante. La única escritura en
el proyecto ocurre bajo `docs/ada-sensei/`.

## RQ-EXM-029 — Nota sugerida identificada
El informe identifica la nota como sugerida y generada por ADA Sensei con el
texto exacto `SUGGESTED_GRADE_LABEL`.

## RQ-EXM-030 — Afirmaciones sustentadas
El sistema distingue evidencias observadas (de archivos del proyecto),
documentadas (del estudiante) e inferidas (del LLM). Las inferencias sin
respaldo de evidencia real se reportan como `unsupported_claims`.

## RQ-EXM-031 — Integridad de métricas
Duración y conteo de consultas se derivan del estado/eventos persistidos.
El conteo de `/ask` se recalcula desde el log de eventos al finalizar; no se
confía en el total almacenado.

## RQ-EXM-032 — Preflight obligatorio
Antes de iniciar, `ProjectPreflight` comprueba que la ruta configurada existe
y es directorio, que se detecta proyecto Android y que Gradle/JDK 17+/Android
SDK están disponibles. `ProjectPreflight` no ejecuta Gradle ni modifica el
proyecto; la validación completa delega la ejecución aislada en
`ToolchainManager`.

## RQ-EXM-033 — Panel de preparación TUI
El TUI presenta un panel de preparación compacto al seleccionar "Iniciar
examen", con estado de proyecto, instrucciones y preflight. El panel usa una
lista de opciones con navegación Arriba/Abajo/Enter/Escape, siguiendo el patrón
`LanguageList`.

## RQ-EXM-034 — Configuración de proyecto
`/project <ruta>` configura y persiste la ruta raíz del proyecto en el contexto
existente. Acepta rutas absolutas y relativas, normaliza `~`, resuelve las
relativas desde el cwd del proceso y no cambia el cwd.

## RQ-EXM-035 — Configuración de instrucciones
`/instructions <ruta>` configura el archivo Markdown del docente. Debe ser un
archivo regular, legible y no vacío con extensión `.md`. La definición se valida
con `ExamDefinitionLoader`. No inicia el examen ni copia/modifica el archivo.

## RQ-EXM-036 — Requisitos obligatorios
No se puede iniciar si falta estudiante, proyecto válido, preflight correcto,
archivo Markdown válido o si ya existe un intento activo. `ExamPreparationService`
devuelve todos los bloqueos conocidos en `ExamPreparationStatus.blockers`.

## RQ-EXM-037 — Revalidación al iniciar
Al confirmar el inicio, se ejecutan todas las validaciones de nuevo. La
validación no crea estado. Si falla, no se crea intento, timer, evento ni docs.

## RQ-EXM-038 — Confirmación explícita
El inicio requiere `confirmed=True` en `ExamStartInput`. Abrir el panel de
preparación no inicia nada. `ExamConfirmationRequired` se lanza cuando
`confirmed=False`.

## RQ-EXM-039 — Temporizador TUI
Durante un examen activo se muestra tiempo transcurrido `HH:MM:SS`. Si hay
`allowed_duration_seconds`, se muestra además tiempo restante y estado de
vencimiento. Si no hay límite, no se inventa un countdown.

## RQ-EXM-040 — Temporizador no bloqueante
La actualización visual es periódica y no bloquea el TUI. Al reanudar, el
tiempo se reconstruye desde `started_at`. Los ticks no se persisten ni puntúan.

## RQ-EXM-041 — Estado de consultas
Durante el examen se muestra el número de `/ask` exitosos y, si está definido,
el límite. El dato procede del event log, no de un contador en memoria.

## RQ-EXM-042 — Límite de tiempo alcanzado
Al agotarse el tiempo se muestra aviso localizado. El examen no se finaliza
automáticamente; el estudiante usa `Finalizar examen`.

## RQ-EXM-043 — Configuración inmutable del intento
Cambiar `/project` durante un examen activo no altera el proyecto asociado al
intento actual; solo afecta un examen posterior.

## RQ-EXM-044 — CLI no interactivo
Los comandos `exam-init --yes` ejecutan las mismas precondiciones que el TUI
incluyendo `ProjectPreflight`. El flag `--yes` no omite ninguna validación.

## RQ-EXM-045 — Localización
Todas las cadenas de UI existen en `es-CO` y `en-US`, con fallback determinista
`en-US`. El intento conserva un snapshot del locale al iniciar (`ExamAttempt.locale`).

## RQ-EXM-046 — Compatibilidad con exámenes anteriores
Las reglas de rúbrica, scoring, evidence pipeline, PDF, persistencia, eventos,
locale y finalización del examen ya existentes se mantienen. Los registros de
intentos anteriores (sin campo `locale`) se leen sin error.

## RQ-EXM-047 — Finalización compacta
La confirmación TUI para finalizar usa el selector compacto de opciones, sin
botones grandes, manteniendo confirmación explícita.

## RQ-EXM-048 — Progreso de finalización
Durante la finalización, el TUI emite mensajes localizados de avance por etapa:
inspección del proyecto, build, pruebas unitarias, Android Lint, Detekt,
interpretación del modelo e informe. Los mensajes se derivan de las etapas
reales del pipeline (`EvidenceCollector` acepta un callback `progress`), nunca
de un temporizador simulado, y no alteran el resultado ni la puntuación.

## RQ-EXM-049 — Apertura del informe
Tras generar el PDF, el TUI lo abre con el visor del sistema de forma
best-effort. Si no hay visor disponible, no falla ni cambia el resultado. La
apertura se controla con `tools.open_report` (activado por defecto). El CLI no
interactivo no abre el PDF.

## RQ-EXM-050 — Ruta del informe en la salida
`ExamFinishResult.report_path` expone la ruta del PDF para que el TUI la muestre
y pueda abrirla.

## RQ-EXM-051 — Detekt: distinción infraestructura vs. hallazgos
`StaticAnalysisTool.run_detekt` distingue:

- Detekt ejecutó y encontró hallazgos → `status="fail"` con evidencias.
- Detekt ejecutó sin hallazgos → `status="pass"`.
- Detekt no está configurado en el proyecto (tarea no encontrada) → `status="missing"` con mensaje de limitación.
- Gradle no disponible → `status="missing"` con mensaje de limitación.

Un fallo de infraestructura (tarea no existe) no reduce la nota del estudiante.
La función `_detekt_not_configured` inspecciona el output de Gradle para
distinguir los casos.

## RQ-EXM-052-DEBUG — Manifest de variante debug opcional
`app/src/debug/AndroidManifest.xml` es un archivo convencional opcional en
proyectos Android. `AndroidProjectAnalyzer` lo registra con `status="info"` al
no encontrarlo (en lugar de `"missing"`). `DimensionScorer._score_architecture`
ignora los registros con `status="info"` al contar deficiencias.

## Matriz de trazabilidad

| Requisito | Componente principal | Prueba |
|---|---|---|
| RQ-EXM-001 | `ExamAttempt`, `ExamResult` | `tests/exams/test_exams_models.py` |
| RQ-EXM-002 | `ExamDefinitionLoader` | `tests/exams/test_definition.py` |
| RQ-EXM-003 | `ExamLifecycle.start` | `tests/exams/test_lifecycle.py` |
| RQ-EXM-004 | `ExamStore`, `ExamAttempt` | `tests/exams/test_lifecycle.py::test_completed_attempt_is_immutable` |
| RQ-EXM-005 | `ExamEventBridge` | `tests/exams/test_ask_tracking.py` |
| RQ-EXM-006 | `ExamEvent`, `ExamStore` | `tests/exams/test_ask_tracking.py::test_ask_event_persisted` |
| RQ-EXM-007 | `ExamLifecycle.finish` | `tests/exams/test_duration.py` |
| RQ-EXM-008 | `DocumentationRules` | `tests/exams/test_docs.py::test_student_documentation_accepted` |
| RQ-EXM-009 | `ExamDocsWriter` | `tests/exams/test_docs.py::test_start_docs_created` |
| RQ-EXM-010 | `EvaluationEngine` | `tests/exams/test_integration.py::test_no_source_modification` |
| RQ-EXM-011 | `ExamineAction.finish` | `tests/exams/test_integration.py::test_instrumented_rejected` |
| RQ-EXM-012 | `ExamScorer.functional_criteria` | `tests/exams/test_integration.py::test_functional_requirements_scored` |
| RQ-EXM-013 | `DimensionScorer._score_static_quality` | `tests/exams/test_scoring.py::test_code_quality_from_deterministic_evidence` |
| RQ-EXM-014 | `architecture_score` | `tests/exams/test_scoring.py` |
| RQ-EXM-015 | `DimensionScorer._score_tests` | `tests/exams/test_scoring.py::test_tests_not_evaluated_when_unavailable` |
| RQ-EXM-016 | `DimensionScorer._score_static_practices` | `tests/exams/test_scoring.py::test_android_practices_from_lint` |
| RQ-EXM-017 | `ExamScorer.process_weights` | `tests/exams/test_process_metrics.py` |
| RQ-EXM-018 | `EXAM_RUBRIC` | `tests/exams/test_exams_rubric.py::test_exam_weights` |
| RQ-EXM-019 | `RubricEngine.score` | `tests/exams/test_scoring.py::test_raw_score_is_deterministic` |
| RQ-EXM-020 | `_raw_score` | `tests/exams/test_scoring.py::test_raw_score_in_range` |
| RQ-EXM-021 | `suggested_grade` | `tests/exams/test_scoring.py::test_grade_conversion` |
| RQ-EXM-022 | `ExamScorer._match` | `tests/exams/test_scoring.py::test_missing_evidence_never_succeeds` |
| RQ-EXM-023 | `ArchitectureAnalyzer` | `tests/exams/test_exams_architecture.py` |
| RQ-EXM-024 | `ExamReportGenerator`, `ExamDocs` | `tests/exams/test_report.py` |
| RQ-EXM-025 | `StructuredPipeline`, `_coerce_array_fields` | `tests/exams/test_exams_structured_output.py` |
| RQ-EXM-085 | `ExamInterpretationAgent`, `ExamInterpretation`, `GroundedClaim` | `tests/exams/test_exams_structured_output.py` |
| RQ-EXM-026 | `ExamineAction._persist` | `tests/exams/test_persistence.py` |
| RQ-EXM-027 | `HistoryStore` | `tests/exams/test_persistence.py::test_history_appended` |
| RQ-EXM-028 | `ExamineAction` | `tests/exams/test_integration.py::test_no_source_modification` |
| RQ-EXM-029 | `SUGGESTED_GRADE_LABEL` | `tests/exams/test_report.py::test_suggested_grade_disclosure` |
| RQ-EXM-030 | `ArchitectureAnalyzer`, `_ground_architecture` | `tests/exams/test_exams_architecture.py::test_observed_documented_inferred` |
| RQ-EXM-031 | `ExamineAction._require_active_attempt` | `tests/exams/test_ask_tracking.py::test_counts_ignore_llm_text` |
| RQ-EXM-032 | `ProjectPreflight` | `tests/exams/test_lifecycle.py` |
| RQ-EXM-033–038 | `ExamPreparationService`, `ExamPreparationScreen` | — |
| RQ-EXM-039–043 | `ExamStatusBar` / TUI | — |
| RQ-EXM-044 | `ExamineAction.start`, CLI | `tests/exams/test_integration.py` |
| RQ-EXM-045 | `ExamAttempt.locale`, `LocaleService` | `tests/exams/test_exam_locale.py` |
| RQ-EXM-046 | — regresión — | suite completa de exámenes |
| RQ-EXM-047–050 | TUI finish, `tools.opener` | — |
| RQ-EXM-051 | `StaticAnalysisTool.run_detekt`, `_detekt_not_configured` | `tests/exams/test_definition.py` (pendiente) |
| RQ-EXM-052-DEBUG | `AndroidProjectAnalyzer._check_optional`, `DimensionScorer._score_architecture` | `tests/exams/test_definition.py` (pendiente) |
| RQ-EXM-076 | `ExamPreparationList.show_preparing`, `ExamPreparationService`, TUI worker | `tests/cli/tui/test_exam_preparation_panel.py`, `tests/cli/tui/test_exam_confirmation.py` |


---


# Adenda normativa — Informe determinista y evaluación integral (2026-11-20)

> Esta adenda reemplaza cualquier regla contradictoria de rúbrica, arquitectura,
> scoring o generación narrativa contenida en versiones anteriores de este
> paquete. Se conserva el flujo de examen, persistencia, preflight, eventos,
> timer y ubicación del PDF salvo donde esta adenda indique lo contrario.
> Decisión de resolución: `exam-default:v1` y `evaluate-default:v1` migran a
> `unified-android:v1` sin alias temporales; los datos persistidos se migran al
> nuevo identificador durante la implementación.

## 1. Responsabilidad de los agentes

### 1.1 Evaluator agent: único responsable de evaluar

`EvaluatorAgent` es el único componente autorizado para inspeccionar evidencias,
aplicar criterios, determinar estados y calcular puntuaciones. Debe evaluar las
cinco dimensiones de la rúbrica unificada y todos sus subcriterios.

Responsabilidades obligatorias:

1. Recibir del `TeacherAgent` el contexto del examen, la definición, el proyecto,
   la documentación permitida y el `EvidenceContext`.
2. Orquestar los analizadores deterministas existentes o especializados.
3. Normalizar los resultados en estructuras tipadas y trazables.
4. Aplicar las reglas de cada tabla de esta adenda.
5. Calcular los puntajes de subcriterios, dimensiones y resultado global.
6. Devolver un `EvaluationReport` estructurado, con evidencias, ubicaciones,
   estado, versión de reglas, limitaciones y cálculos reproducibles.

`EvaluatorAgent` no puede delegar la decisión de cumplimiento ni el cálculo de
notas al LLM. Los analizadores pueden usar heurísticas estáticas deterministas;
toda regla debe estar versionada, ser testeable y producir evidencia.

### 1.2 Teacher agent: consumidor y coordinador

`TeacherAgent` es el único agente que interactúa pedagógicamente con el estudiante.
Usa el resultado de `EvaluatorAgent` para:

- explicar el resultado y resolver preguntas;
- mostrar resumen, dimensiones, criterios, hallazgos y recomendaciones ya
  estructuradas;
- orientar al estudiante sobre cómo corregir hallazgos;
- decidir qué contenido pedagógico presentar según la etapa de aprendizaje;
- solicitar una nueva evaluación cuando corresponda.

`TeacherAgent` no inspecciona el proyecto para emitir una segunda nota, no
recalcula puntuaciones, no altera estados y no inventa hallazgos. No debe
reformular el reporte oficial como narrativa libre. Puede explicar un hallazgo,
pero debe citar su `finding_id` y conservar su significado.

### 1.3 Flujo de interacción entre componentes

```text
Human Student
     ↕
TeacherAgent
     ↕  (EvaluationRequest / EvaluationReport)
EvaluatorAgent
     ↓
Evidence Collectors + Deterministic Analyzers
     ↓
Rubric Engine + Score Calculator
     ↓
EvaluationReport (typed, versioned, traceable)
     ↙                         ↘
TeacherAgent                PDF Report Generator
     ↓
Student feedback / learning guidance
```

El PDF se genera exclusivamente desde `EvaluationReport`. El `TeacherAgent` no
redacta ni modifica el PDF.

## 2. Rúbrica global única

La misma rúbrica se usa en `/evaluate` y en los exámenes. Se elimina la antigua
diferencia entre rúbrica de evaluación general y rúbrica de examen.

| ID | Dimensión | Peso global |
|---|---|---:|
| D1 | Requisitos funcionales / funcionalidad | 40% |
| D2 | Pruebas unitarias | 20% |
| D3 | Calidad del código | 15% |
| D4 | Arquitectura MVVM | 15% |
| D5 | Buenas prácticas Android | 10% |
| | **Total** | **100%** |

Reglas globales:

- Cada dimensión y subcriterio se puntúa en escala `0.00–5.00`.
- `weighted_contribution = dimension_score × dimension_weight`.
- `final_score_5 = Σ weighted_contribution` cuando las cinco dimensiones
  fueron evaluadas completamente.
- `final_score_50 = final_score_5 × 10`.
- `suggested_grade` se deriva con la conversión ya definida por el sistema,
  ajustada para que el rango sea 1.0–5.0:
  `round(1.0 + (final_score_5 / 5.0) × 4.0, 1)`.
- No se renormaliza silenciosamente una evaluación parcial para aparentar que
  fue integral. Si falta evidencia, se muestra `NOT_EVALUATED`, el peso excluido
  y no se presenta un resultado como evaluación completa.
- Una herramienta no configurada, no disponible o con error de infraestructura
  nunca se convierte en cero ni en incumplimiento del estudiante.
- La ausencia de evidencia de un requisito sí impide declararlo aprobado, pero
  debe distinguirse de un fallo demostrado.

## 3. Reglas comunes de estado y evidencia

Todos los criterios y analizadores deben usar estos estados:

| Estado | Regla | Efecto en puntuación |
|---|---|---|
| `PASS` | Evidencia verificable satisface el criterio completo | Puntaje según regla del criterio |
| `PARTIAL` | Evidencia verificable satisface solo parte del criterio | Puntaje parcial según regla explícita |
| `FAIL` | Evidencia verificable demuestra que el criterio no se cumple | 0 para el criterio afectado |
| `NOT_EVALUATED` | No existe evidencia suficiente o el criterio no aplica | Se excluye; se declara motivo |
| `NOT_CONFIGURED` | Herramienta/regla requerida no está configurada | No penaliza; requiere resolver cobertura |
| `NOT_AVAILABLE` | Dependencia o entorno no disponible | No penaliza; requiere resolver cobertura |
| `EXECUTION_ERROR` | El analizador no pudo completar por error técnico | No penaliza; requiere resolver cobertura |
| `INFO` | Hallazgo informativo sin incumplimiento | No afecta nota |

Cada `CriterionResult` incluye obligatoriamente:
`criterion_id`, `status`, `score`, `weight`, `weighted_score`, `evidence_ids`,
`finding_ids`, `reason_code`, `analyzer`, `analyzer_version` y `rule_version`.
`score` y `weighted_score` son nulos para estados no evaluables.

Una evidencia debe contener `evidence_id`, tipo, ruta relativa, línea/rango
cuando aplique, regla que la produjo, resumen factual, comando/herramienta,
versión, timestamp y hash del artefacto cuando sea posible. No se aceptan
ubicaciones inventadas.

## 4. D1 — Requisitos funcionales (40%)

### Tabla D1.1 — Evaluación de cada requisito

Cada requisito definido por el docente se convierte en un criterio independiente.
El peso funcional de todos los requisitos debe sumar exactamente 1.0.

| Estado del requisito | Regla determinista | Nota |
|---|---|---:|
| `PASS` | Todos los casos de aceptación verificables asociados al requisito pasan | 5.00 |
| `PARTIAL` | Al menos un caso pasa y al menos uno falla, o se demuestra cumplimiento parcial | 2.50 |
| `FAIL` | Los casos ejecutados demuestran que el comportamiento requerido falla | 0.00 |
| `NOT_EVALUATED` | No existe prueba/evidencia suficiente para decidir | Excluido |

`NOT_EVALUATED` no equivale a `FAIL`. Si un requisito carece de casos de
aceptación, `RequirementMatcher` debe producir una limitación explícita; no
puede marcarlo como aprobado solo por encontrar una clase, método o palabra
clave.

### Tabla D1.2 — Cálculo de la dimensión

`functional_score = Σ(requirement_score × normalized_requirement_weight) /
Σ(weights of evaluated requirements)`.

La dimensión solo se declara completa cuando todos los requisitos ponderados
tienen resultado evaluable. El reporte muestra total de requisitos, aprobados,
parciales, fallidos y no evaluados, además de la tabla individual.

## 5. D2 — Pruebas unitarias (20%)

### Tabla D2.1 — Subcriterios

| ID | Subcriterio | Peso interno | Regla determinista |
|---|---|---:|---|
| T1 | Cobertura de requisitos por pruebas unitarias | 50% | Requisitos con al menos una prueba unitaria asociada / total de requisitos funcionales |
| T2 | Resultado de ejecución | 35% | Pruebas aprobadas / (aprobadas + fallidas); errores de infraestructura se excluyen |
| T3 | Trazabilidad y calidad de asociación | 15% | Cada asociación debe apuntar a test real y requisito existente; se puntúa la proporción de asociaciones válidas |

Regla del umbral solicitado: T1 debe alcanzar al menos 80% para cumplir el
umbral mínimo de cobertura. El reporte siempre muestra porcentaje real. Estar
por debajo del 80% no se oculta ni se convierte automáticamente en `FAIL` de
todas las pruebas; se marca `PARTIAL` en T1 y se aplica la escala proporcional.

### Tabla D2.2 — Fórmulas

- `coverage_ratio = covered_requirements / total_functional_requirements`.
- `T1_score = min(5, coverage_ratio / 0.80 × 5)`. Se muestra además el booleano
  `coverage_threshold_met = coverage_ratio >= 0.80`.
- `execution_ratio = passed_tests / (passed_tests + failed_tests)`.
  `T2_score = execution_ratio × 5`. Si no se ejecutó ninguna prueba por
  `NOT_AVAILABLE`, `NOT_CONFIGURED` o `EXECUTION_ERROR`, T2 es `NOT_EVALUATED`.
  Si se ejecutó correctamente el runner y no hay pruebas definidas, T2 es
  `FAIL` con nota 0.
- `T3_score = valid_test_requirement_links / total_declared_test_requirement_links × 5`.
  Si no existen asociaciones declaradas ni inferibles con certeza, T3 es
  `NOT_EVALUATED`.
- `tests_score = 0.50×T1 + 0.35×T2 + 0.15×T3`, normalizado solo con subcriterios
  evaluables y declarando cobertura.

El informe separa conteo de pruebas (`passed`, `failed`, `skipped`, `error`),
cobertura de requisitos y cobertura de líneas si una herramienta la ofrece.
La cobertura de líneas nunca sustituye la cobertura de requisitos.

## 6. D3 — Calidad del código (15%)

### Tabla D3.1 — Herramientas y pesos internos

| Herramienta | Peso interno | Qué evalúa |
|---|---:|---|
| Detekt | 40% | Complejidad, code smells, tamaño de métodos/clases y reglas Kotlin |
| Android Lint | 35% | Problemas estáticos Android, recursos, manifest, APIs, seguridad, accesibilidad y rendimiento |
| KtLint | 25% | Convenciones y formato del código Kotlin |
| **Total** | **100%** | |

### Tabla D3.2 — Normalización de hallazgos por severidad

Para cada herramienta se cuentan hallazgos únicos por regla y ubicación. Duplicados
del mismo hallazgo se consolidan.

| Severidad normalizada | Penalización por hallazgo |
|---|---:|
| `ERROR` / `FATAL` | 1.00 |
| `WARNING` | 0.50 |
| `INFO` | 0.10 |
| `STYLE` | 0.10 |

`quality_tool_score = max(0, 5 − Σ(penalizaciones))`. Los hallazgos se limitan
a una penalización máxima de 5 puntos por herramienta. La severidad original
se conserva junto a la severidad normalizada. Las reglas de mapeo de severidad
son versionadas y específicas de cada analizador.

Una herramienta solo recibe puntuación si ejecutó correctamente. Si no está
configurada o no pudo ejecutarse, su subcriterio es `NOT_CONFIGURED`,
`NOT_AVAILABLE` o `EXECUTION_ERROR`, nunca 5 ni 0.

`code_quality_score = 0.40×Detekt + 0.35×AndroidLint + 0.25×KtLint`,
normalizado sobre herramientas evaluables y con cobertura visible. La dimensión
no se presenta como completa si alguna herramienta requerida no fue evaluada.

### Tabla D3.3 — Campos obligatorios de cada hallazgo

| Campo | Regla |
|---|---|
| `finding_id` | Identificador estable y único |
| `tool` / `rule_id` | Herramienta y regla exacta que lo produjo |
| `severity` | Severidad original y normalizada |
| `message` | Mensaje original conciso; no reescrito por LLM |
| `file` / `line` | Ruta relativa y línea real si existen |
| `recommendation_code` | Código de recomendación del catálogo versionado |
| `evidence_id` | Evidencia de ejecución que respalda el hallazgo |

## 7. D4 — Arquitectura MVVM (15%)

La dimensión evalúa explícitamente MVVM. Se elimina `clean_architecture` como
dimensión y no se exige Clean Architecture, Use Cases ni capas adicionales para
obtener puntaje.

### Tabla D4.1 — Subcriterios MVVM

| ID | Subcriterio | Peso interno | Regla de evaluación |
|---|---|---:|---|
| M1 | Separación Model / View / ViewModel | 30% | Identifica componentes y verifica responsabilidades; la UI no concentra lógica de dominio |
| M2 | Independencia de ViewModel respecto a View | 25% | ViewModel no importa ni referencia Activities, Fragments, Views o composables concretos |
| M3 | Estado y flujo unidireccional | 20% | Estado observable expuesto por ViewModel; eventos de UI enviados como acciones; no duplicación inconsistente de estado |
| M4 | Acceso a datos y dependencias | 15% | ViewModel depende de abstracciones/repositorios y no implementa directamente acceso de bajo nivel cuando el proyecto requiere repositorio |
| M5 | Pruebas de ViewModel | 10% | ViewModels con lógica comprobable y pruebas unitarias asociadas |

### Tabla D4.2 — Reglas de puntuación por subcriterio

| Resultado verificable | Estado | Nota |
|---|---|---:|
| Todos los indicadores aplicables pasan | `PASS` | 5.00 |
| Algunos indicadores pasan y otros fallan | `PARTIAL` | 2.50, o proporción exacta de indicadores si hay conteo objetivo |
| La evidencia demuestra incumplimiento | `FAIL` | 0.00 |
| Proyecto/estructura insuficiente para concluir | `NOT_EVALUATED` | Excluido |

El analizador debe inspeccionar imports, referencias de tipos, dependencias,
flujos de estado, estructura de paquetes y pruebas. El nombre `ViewModel`,
`Repository` o `Model` por sí solo no prueba cumplimiento. Cada decisión debe
incluir referencias a archivos/líneas y regla aplicada.

`mvvm_score = Σ(subcriterion_score × internal_weight)` sobre subcriterios
evaluables; debe mostrar cobertura. No se otorga puntuación por Clean Architecture.

## 8. D5 — Buenas prácticas Android (10%)

### Tabla D5.1 — Subcriterios y pesos internos

| ID | Subcriterio | Peso interno | Indicadores verificables |
|---|---|---:|---|
| A1 | Ciclo de vida y componentes Android | 15% | Uso correcto de lifecycle; ViewModel asociado al ciclo de vida; ausencia de referencias a Activity/Context retenidas indebidamente; manejo de estado ante recreación |
| A2 | Jetpack Compose y gestión de estado | 20% | State hoisting; flujo unidireccional; estado observable; composables con responsabilidades acotadas; efectos (`LaunchedEffect`, `DisposableEffect`) usados con claves apropiadas |
| A3 | Recursos y configuración Android | 10% | Strings/dimensiones/colores externalizados; manifest coherente; configuración por variantes; soporte de configuración/localización |
| A4 | Concurrencia y operaciones asíncronas | 15% | Coroutines/Flow apropiados; `viewModelScope`/lifecycle-aware collection; cancelación; no bloquear main thread |
| A5 | Seguridad y permisos | 15% | Permisos mínimos; runtime permissions cuando aplican; no secretos hardcoded; almacenamiento y comunicaciones seguras; validación de entradas |
| A6 | Adaptabilidad y accesibilidad | 15% | Content descriptions; contraste; escalado de texto; targets táctiles; layouts adaptables; navegación accesible |
| A7 | Compatibilidad y uso de APIs | 10% | minSdk/targetSdk coherentes; APIs disponibles para SDK objetivo; manejo de deprecated APIs; compatibilidad de dependencias |

### Tabla D5.2 — Reglas de evaluación

Cada indicador aplicable se registra como `PASS`, `PARTIAL`, `FAIL` o
`NOT_EVALUATED`. El subcriterio se puntúa proporcionalmente:
`criterion_score = 5 × passed_indicator_points / total_applicable_indicator_points`,
donde `PASS=1`, `PARTIAL=0.5`, `FAIL=0`. Indicadores no aplicables se excluyen
del denominador con razón documentada.

El analizador combina Android Lint, inspección de manifest/Gradle/recursos,
análisis estático de Kotlin/Compose y reglas específicas de ADA Sensei. Un
hallazgo de Lint puede respaldar A3, A5, A6 o A7, pero no se debe contar dos
veces dentro de D5. La puntuación de D3 mide calidad general del código; D5
mide cumplimiento específico de plataforma Android. La misma evidencia puede
referenciarse en ambas dimensiones solo si demuestra criterios distintos.

## 9. Tabla de cobertura de analizadores

| Analizador | Dimensiones que alimenta | Evidencia mínima de salida |
|---|---|---|
| Project/Gradle inspector | D1, D4, D5 | módulos, plugins, SDK, dependencias, estructura |
| Build tool | D1, D2, D4, D5 | resultado, tareas, errores y artefactos |
| Unit test analyzer | D1, D2, D4 | tests, resultados, asociaciones requisito-test |
| Requirement matcher | D1, D2 | casos de aceptación y enlaces a evidencias |
| Detekt | D3, señales auxiliares D4/D5 solo si hay regla explícita | findings JSON/XML |
| Android Lint | D3, D5 | findings XML/HTML con issue id, severidad, ubicación |
| KtLint | D3 | findings estructurados y ubicación |
| MVVM analyzer | D4 | dependencias, imports, flujos de estado, evidencias |
| Android practices analyzer | D5 | resultado por indicador y evidencia |
| Documentation analyzer | contexto/evidencia de apoyo | documentos hallados, legibilidad y referencias |

Cada dimensión debe contar con un `AnalyzerCoverage` que identifique
analizadores requeridos, ejecutados, no configurados, no disponibles, fallidos
y criterios cubiertos. El informe debe evaluar todo lo que el entorno permita;
no debe declarar evaluación integral si falta evidencia necesaria.

## 10. Contrato estructurado del EvaluatorAgent

`EvaluatorAgent.evaluate(request) -> EvaluationReport`.

`EvaluationReport` debe incluir al menos:

- `report_id`, `student_id`, `project_id`, `exam_id`, `attempt_id`;
- `generated_at`, `locale`, `rubric_id`, `rubric_version`;
- `overall_status`: `COMPLETE`, `PARTIAL` o `BLOCKED`;
- `overall_score_5`, `overall_score_50`, `suggested_grade` (nullable si parcial
  según política de divulgación);
- `dimension_results[]`;
- `criterion_results[]`;
- `requirement_results[]`;
- `test_summary`;
- `tool_runs[]`;
- `findings[]`;
- `evidence[]`;
- `analyzer_coverage[]`;
- `limitations[]`;
- `calculation_trace[]`;
- `ruleset_versions`.

El contrato debe ser Pydantic y validarse antes de persistir o generar el PDF.
Todos los cálculos se reconstruyen desde los resultados tipados. No se permite
que el LLM complete campos numéricos faltantes.

## 11. Especificación del PDF: tablas y reglas de cada tabla

El PDF oficial es un informe técnico generado directamente desde
`EvaluationReport`; ocupa las páginas que exija su contenido y no impone un
límite fijo. No elimina secciones obligatorias ni evidencias para reducir
páginas, evita páginas vacías o contenido cortado y numera cada página. Sin
párrafos de interpretación libre, sin fortalezas/debilidades generadas por LLM
y sin conclusiones conversacionales. Usa títulos, tablas, indicadores, estados
y hallazgos concretos. Las etiquetas se localizan mediante catálogos `es-CO` y
`en-US`; los IDs y códigos permanecen.

### Tabla R1 — Identificación

| Campo | Fuente | Regla |
|---|---|---|
| Estudiante | `ExamAttempt.student_id` / perfil | No inferir del enunciado |
| Proyecto | ruta/identidad del proyecto del intento | Mostrar nombre y ruta relativa si procede |
| Examen | `ExamDefinition` | Título e ID/versionado |
| Fecha | `finished_at` / zona horaria configurada | Formato local |
| Rúbrica | `rubric_id`, `rubric_version` | Mostrar versión exacta |
| Estado | `overall_status` | COMPLETE/PARTIAL/BLOCKED localizado |

### Tabla R2 — Resumen global

| Columna | Regla |
|---|---|
| Puntaje | Mostrar `overall_score_5` solo si la política permite divulgarlo |
| Porcentaje | `overall_score_5 / 5 × 100` |
| Dimensiones evaluadas | Conteo de dimensiones completas/evaluables |
| Cobertura | Peso global evaluado / 100 |
| Estado | `COMPLETE`, `PARTIAL` o `BLOCKED` |

No mostrar `COMPLETE` si cualquier dimensión global requerida está sin evaluar.

### Tabla R3 — Resultado por dimensión

Columnas obligatorias: ID, dimensión, peso global, nota 0–5, contribución
ponderada, estado, cobertura. La contribución es `score × weight`; el formato
de porcentaje/puntos debe estar rotulado sin ambigüedad. Las dimensiones no
evaluadas muestran `—` y su `reason_code`, nunca cero.

### Tabla R4 — Requisitos funcionales

Una fila por requisito: ID, descripción abreviada del docente, peso funcional,
estado, nota, casos aprobados/total, evidencia IDs y archivos/líneas. Orden por
ID original. No parafrasear ni inventar requisitos.

### Tabla R5 — Pruebas unitarias

Mostrar: total ejecutadas, aprobadas, fallidas, omitidas, errores; requisitos
cubiertos/total y porcentaje; cumplimiento del umbral 80%; T1/T2/T3 y sus
pesos/notas. Mostrar cobertura de líneas solo si existe reporte de herramienta,
en fila separada y nunca como sustituto de cobertura de requisitos.

### Tabla R6 — Calidad del código

Una fila por Detekt, Android Lint y KtLint con peso interno, estado de ejecución,
versión, total por severidad, nota, aporte a D3. Después, tabla de hallazgos con
finding ID, regla, severidad, mensaje original, archivo/línea y recomendación
codificada. Orden: severidad descendente, luego archivo y línea.

### Tabla R7 — Arquitectura MVVM

Una fila por M1–M5 con descripción, peso interno, estado, nota, aporte, evidencia
y archivos/líneas. No usar la etiqueta Clean Architecture ni puntuar capas no
exigidas por MVVM.

### Tabla R8 — Buenas prácticas Android

Una fila por A1–A7 con descripción, peso interno, nota, estado, indicadores
PASS/PARTIAL/FAIL/NOT_EVALUATED y evidencias. Mostrar razón para indicadores no
aplicables.

### Tabla R9 — Estado de herramientas

Una fila por herramienta: nombre, versión, comando/tarea, estado, duración,
artefacto de salida, limitación. Los estados de infraestructura no son
hallazgos del estudiante.

### Tabla R10 — Métricas del examen

Mostrar duración real desde `started_at` y `finished_at`, número de `/ask`
exitosos desde `ASK_COMPLETED`, límites configurados y cumplimiento. Son
métricas informativas y no afectan la rúbrica unificada de cinco dimensiones.

### Tabla R11 — Observaciones deterministas

Cada observación se crea solo mediante una regla codificada con `observation_id`,
`trigger_rule_id`, `severity`, `message_template_id`, `evidence_ids` y
`finding_ids`. El texto se resuelve desde plantillas localizadas. No se admiten
párrafos libres del LLM.

### Tabla R12 — Limitaciones y trazabilidad

Mostrar criterio/dimensión afectada, estado de herramienta, código de motivo,
descripción factual, impacto en cobertura y acción técnica requerida. Incluir
versiones de analizadores y reglas para reproducibilidad.

## 12. Plantillas de observaciones y recomendaciones

Las observaciones son mensajes de catálogo. Ejemplos:

| Código | Condición | Plantilla |
|---|---|---|
| OBS-QUALITY-001 | Hallazgos Detekt > 0 | `Se detectaron {count} hallazgos en Detekt.` |
| OBS-LINT-001 | Hallazgos Android Lint > 0 | `Se detectaron {count} hallazgos en Android Lint.` |
| OBS-KTLINT-001 | Hallazgos KtLint > 0 | `Se detectaron {count} hallazgos de estilo en KtLint.` |
| OBS-TEST-001 | Cobertura de requisitos < 80% | `La cobertura de requisitos por pruebas unitarias es {coverage}; el mínimo definido es 80%.` |
| OBS-MVVM-001 | Criterios MVVM en PARTIAL/FAIL | `El criterio {criterion_id} de MVVM tiene estado {status}.` |
| OBS-ANDROID-001 | Indicadores Android en PARTIAL/FAIL | `El subcriterio {criterion_id} presenta {count} indicadores no aprobados.` |
| OBS-TOOL-001 | Analizador no ejecutable | `{tool} no pudo evaluarse: {reason}. No se aplicó penalización.` |

Recomendaciones: catálogo estático por `rule_id` y `finding_id`, con texto de
acción concreto. El LLM puede ampliar la explicación durante una conversación
del TeacherAgent, pero no puede cambiar la observación oficial.

## 13. Regla de uso del LLM

Para el reporte de evaluación, el LLM queda fuera de:
- detección de cumplimiento;
- asociación definitiva de requisitos con pruebas;
- asignación de estados;
- severidad y conteo de hallazgos;
- puntuación de criterios/dimensiones;
- cálculo de nota y porcentaje;
- generación de observaciones oficiales;
- creación o edición del PDF.

El LLM solo puede asistir al `TeacherAgent` en tutoría y explicación posterior,
siempre con referencias a `finding_id`, `criterion_id` o `evidence_id`. Las
respuestas pedagógicas no se incorporan automáticamente al informe oficial.

## 14. Pruebas de aceptación obligatorias

1. Mismos archivos, mismas versiones de herramientas y mismo ruleset producen
   exactamente el mismo `EvaluationReport` numérico.
2. Ninguna respuesta del LLM puede alterar el resultado al cambiar, fallar o
   devolver JSON inválido.
3. Las cinco dimensiones aparecen siempre en el PDF, incluso si alguna tiene
   `NOT_EVALUATED`.
4. Todas las tablas R1–R12 se generan desde el contrato tipado.
5. El reporte no contiene prosa libre ni conclusión del LLM.
6. Toda nota tiene un `calculation_trace` reproducible.
7. Toda observación oficial enlaza regla, evidencia y/o hallazgo.
8. `NOT_CONFIGURED`, `NOT_AVAILABLE` y `EXECUTION_ERROR` no se convierten en
   `FAIL` ni en cero.
9. Los pesos globales suman 100%; los pesos internos D3, D4 y D5 suman 100%.
10. El umbral del 80% de cobertura de requisitos por pruebas se calcula y se
    muestra correctamente en los límites 79.99%, 80% y 100%.
11. Las reglas de no aplicabilidad excluyen solo el indicador afectado y
    conservan el peso excluido visible.
12. El `TeacherAgent` presenta el reporte sin modificarlo y puede explicar un
    hallazgo por su ID.
13. `/evaluate` y `/exam` usan el mismo `RubricDefinition` versionado.
14. Regresión con Domino Conquista: todos los requisitos del enunciado se cargan,
    se enlazan con evidencia real y se reportan sin asumir resultados.


## Adenda normativa — Definición de examen exclusivamente JSON (v1)

> Decisión de resolución: el requisito legado «Manifest de variante debug opcional»
> se identifica ahora como `RQ-EXM-052-DEBUG`. Los identificadores `RQ-EXM-052` a
> `RQ-EXM-063` quedan reservados para esta adenda JSON y `RQ-EXM-064` a
> `RQ-EXM-075` para la adenda de toolchain.

**Esta adenda prevalece sobre cualquier sección anterior que permita Markdown o PDF como fuente autoritativa de requisitos.** En esta versión, el docente debe entregar un archivo JSON estructurado. La extracción automática desde documentos queda fuera de alcance.

### Fuente única de requisitos
- `ExamDefinitionLoader` acepta únicamente `.json` para la definición del examen.
- El JSON validado contra `exam-definition.schema.json` es la fuente única de verdad de requisitos, criterios de aceptación, pesos, límites y referencias.
- Markdown/PDF pueden existir como material de lectura, pero no se parsean ni se usan para crear requisitos o asignar pesos.
- El docente es responsable de definir y revisar los requisitos antes de iniciar.
- No se permite que `EvaluatorAgent` invente, complete, renombre, elimine o cambie requisitos.

### Requisito normalizado
Cada requisito contiene `id`, `type`, `title`, `description`, `weight`, `source` y `acceptance_criteria`. Cada criterio de aceptación define `id`, `description` y al menos un método de verificación. Los IDs son estables y únicos. `source` identifica archivo/sección/referencia del material docente.

### Validación del JSON
1. Validar sintaxis JSON y JSON Schema antes de crear un intento.
2. Rechazar propiedades desconocidas, campos obligatorios ausentes, IDs duplicados, pesos fuera de rango y criterios sin método de verificación.
3. Los pesos de requisitos `functional` deben sumar exactamente 1.0; otros tipos no participan en esa suma.
4. Verificar que `rubric_ref` exista y sea compatible con la rúbrica unificada.
5. Si hay errores, bloquear el inicio y devolver errores por JSON Pointer (`/requirements/0/weight`, etc.). No intentar reparar automáticamente el archivo con el LLM.
6. Conservar hash SHA-256, versión y copia inmutable del JSON validado en el snapshot del `ExamAttempt`.

### Relación entre requisitos y rúbrica
- Los requisitos `functional` alimentan D1 (40%).
- `technical` y `documentation` aportan evidencia a las dimensiones correspondientes, pero no crean dimensiones ni pesos globales adicionales.
- D2 (20%) se calcula desde pruebas unitarias ejecutadas y su asociación explícita a requisitos/criterios. El umbral mínimo es 80% de requisitos funcionales con al menos una prueba unitaria asociada; no equivale a cobertura de líneas.
- D3 (15%) usa Detekt 40%, Android Lint 35% y KtLint 25%.
- D4 (15%) evalúa MVVM con los subcriterios versionados de la rúbrica.
- D5 (10%) evalúa los siete subcriterios de buenas prácticas Android versionados en la rúbrica.
- La definición del examen no puede sobrescribir pesos de la rúbrica global. Solo `rubric_ref` selecciona una versión publicada.

### Responsabilidad de agentes
- `TeacherAgent` solicita y carga el JSON, presenta errores de validación al docente/estudiante y coordina el flujo. No interpreta requisitos para calificarlos ni calcula notas.
- `EvaluatorAgent` consume exclusivamente el `ExamDefinition` validado, coordina analizadores, relaciona evidencias con criterios, aplica la rúbrica determinista y produce `EvaluationReport`.
- Los analizadores producen evidencias estructuradas; no asignan notas globales.
- `TeacherAgent` consume `EvaluationReport` para explicarlo. No lo modifica.

### No inferencia de requisitos
El análisis del código puede descubrir componentes o comportamientos no declarados, pero estos se reportan como `unmapped_observations`; nunca se convierten automáticamente en requisitos ni afectan la nota. Un requisito sin evidencia suficiente queda `NOT_EVALUATED` o `NOT_MET` según la regla de evaluación y evidencia disponible; la ausencia de evidencia no se convierte en aprobación.


## Requisitos adicionales — JSON docente obligatorio

- **RQ-EXM-052 — Fuente JSON única:** `ExamDefinitionLoader` acepta únicamente una definición `.json` validada para iniciar un examen. Markdown/PDF no generan requisitos.
- **RQ-EXM-053 — JSON Schema versionado:** el paquete incluye `exam-definition.schema.json`; toda definición debe cumplirlo antes del preflight final.
- **RQ-EXM-054 — Requisitos explícitos:** cada requisito tiene ID único, tipo, título, descripción, peso funcional cuando aplique, procedencia y criterios de aceptación verificables.
- **RQ-EXM-055 — Validación estricta:** se rechazan IDs duplicados, propiedades desconocidas, referencias inválidas, pesos incorrectos y criterios sin métodos de verificación. No hay autocorrección por LLM.
- **RQ-EXM-056 — Pesos funcionales:** los pesos de requisitos `functional` suman exactamente 1.0. Los demás tipos no participan en esa suma.
- **RQ-EXM-057 — Rúbrica externa inmutable:** `rubric_ref` apunta a la rúbrica unificada versionada; el JSON del docente no puede alterar los pesos globales ni subpesos.
- **RQ-EXM-058 — Snapshot de definición:** el intento guarda copia inmutable y SHA-256 de la definición JSON validada.
- **RQ-EXM-059 — Errores accionables:** los errores de validación indican JSON Pointer, código y mensaje localizado; cualquier error bloquea el inicio.
- **RQ-EXM-060 — TeacherAgent coordinador:** TeacherAgent carga/valida y coordina; no califica, no asigna estados y no modifica puntuaciones.
- **RQ-EXM-061 — EvaluatorAgent evaluador único:** EvaluatorAgent evalúa únicamente requisitos del `ExamDefinition` validado y produce `EvaluationReport` estructurado.
- **RQ-EXM-062 — Observaciones no mapeadas:** funcionalidades encontradas sin requisito correspondiente se reportan como `unmapped_observations` y no afectan el puntaje.
- **RQ-EXM-063 — Métodos de verificación permitidos:** cada criterio especifica uno o más métodos soportados (`unit_test`, `build`, `static_analysis`, `source_inspection`, `ui_inspection`, `manual_review`, `documentation_check`).


# Adenda normativa — Preparación y gestión automática del toolchain estático (2026-11-21)

Esta adenda prevalece sobre cualquier regla anterior que permita continuar una
evaluación completa con Detekt o KtLint sin configurar, o con Android Lint sin
ingresar al pipeline. La ausencia de una herramienta requerida debe resolverse
antes de evaluar; si no puede resolverse, el intento queda bloqueado o
`INCOMPLETE_INFRASTRUCTURE`, nunca se interpreta como fallo del estudiante.

## Responsabilidad y orquestación

- `EvaluatorAgent` es el único responsable de solicitar la preparación del
  entorno, verificarla, ejecutar los analizadores, evaluar evidencias y producir
  `EvaluationReport`.
- `EvaluatorAgent` delega la preparación técnica en `ToolchainManager`; no
  instala paquetes directamente ni delega decisiones de calificación.
- `TeacherAgent` solo coordina la interacción, presenta el estado de preparación
  y comunica el resultado. No instala herramientas, no ejecuta análisis, no
  puntúa y no cambia estados.
- `ToolchainManager` es un servicio determinista sin LLM. Resuelve versiones
  compatibles, configura un entorno aislado, ejecuta verificaciones de salud y
  devuelve `ToolchainManifest` y `ToolchainPreparationResult`.

## Herramientas requeridas

| Herramienta | Gestión | Comprobación obligatoria | Uso |
|---|---|---|---|
| Android Lint | Integrado en Android Gradle Plugin (AGP); detectar variante y tarea `lint<Variant>`/`lint` | Ejecutar tarea y validar resultado estructurado XML/HTML | D3 y criterios Android aplicables |
| Detekt | Resolver plugin/versión compatible con Kotlin y Gradle; configurar en entorno aislado | Ejecutar tarea Detekt y validar reporte XML/SARIF/HTML disponible | D3 |
| KtLint | Resolver plugin/CLI y versión fijada en política de toolchain | Ejecutar `check` y validar reporte estructurado | D3 |

Android Lint no se instala como herramienta independiente cuando ya lo provee
AGP. Si AGP no expone una tarea Lint compatible, `ToolchainManager` debe
determinar si existe una ruta de configuración aislada soportada; no debe
inventar una tarea ni reportar éxito por detectar AGP solamente.

## Política de instalación y compatibilidad

1. Las versiones de Detekt, KtLint, Gradle, Kotlin y AGP deben proceder de una
   matriz versionada y probada (`toolchain-policy.json`), nunca de `latest`.
2. `ToolchainManager` detecta JDK, Gradle wrapper, Kotlin, AGP, módulos,
   variantes y tareas disponibles antes de resolver herramientas.
3. La resolución de dependencias se realiza mediante Gradle/plugin repositories
   permitidos y caché de ADA Sensei. Debe registrar coordenadas, versión,
   checksum cuando esté disponible y origen.
4. No se ejecutan instaladores globales ni se modifica el entorno global del
   sistema del estudiante. Las dependencias quedan en la caché aislada de ADA
   Sensei o en un workspace temporal de evaluación.
5. No se modifica permanentemente ningún archivo del proyecto del estudiante.
   La configuración faltante se aplica en un workspace temporal/copia de
   evaluación o mediante mecanismos Gradle aislados previamente probados. Si
   una configuración requiere editar el proyecto original y no existe una
   alternativa reversible y verificable, se detiene y solicita intervención.
6. Si se usa una copia temporal, se conserva la estructura relativa, se excluyen
   secretos y artefactos innecesarios, y se registra el hash del snapshot.
7. La instalación/configuración ocurre durante preflight, antes de crear el
   intento y antes de iniciar el temporizador del examen.
8. Se permite cachear artefactos por versión y checksum; no se reutiliza una
   configuración incompatible con el proyecto actual.
9. No se descarga ni ejecuta código de repositorios no confiables sin las
   restricciones de seguridad definidas por ADA Sensei. Los repositorios y
   mirrors permitidos son configurables y auditables.
10. Si no hay red, repositorio, permisos o compatibilidad suficiente, se informa
    la causa exacta y no se declara toolchain listo.

## Estados normalizados

`ToolchainPreparationResult` y cada `ToolExecutionEvidence` usan estados:

- `READY`: versión compatible detectada/configurada y ejecución de prueba
  satisfactoria.
- `INSTALLED`: dependencia resuelta en caché aislada, aún requiere health check.
- `CONFIGURED`: tarea/configuración aislada aplicada, aún requiere health check.
- `ISSUES_FOUND`: herramienta ejecutó correctamente y reportó hallazgos reales.
- `NOT_CONFIGURED`: no se pudo configurar de forma segura/compatible.
- `NOT_AVAILABLE`: dependencia/entorno/repository no disponible.
- `INCOMPATIBLE`: versiones incompatibles o no soportadas por la matriz.
- `EXECUTION_ERROR`: herramienta configurada pero no pudo completar ejecución.
- `SKIPPED_NOT_APPLICABLE`: solo para reglas o subcriterios declarados no aplicables;
  no puede usarse para omitir Detekt, KtLint o Android Lint requeridos en D3.

La herramienta solo se considera evaluada cuando `health_check=PASS`, el comando
real se ejecutó y se generó/validó un reporte interpretable. Encontrar el plugin,
la tarea o un archivo de configuración no demuestra ejecución correcta.

## Bloqueo y calificación

- El preflight debe asegurar que las tres herramientas requeridas están listas
  antes de iniciar el examen: `READY` o `ISSUES_FOUND` con `health_check=PASS` y
  reporte estructurado válido. Si falta una, intenta resolverla automáticamente
  dentro de los límites de seguridad anteriores.
- Si la resolución falla, no se crea `ExamAttempt`, no inicia timer y no se
  evalúa al estudiante. El `TeacherAgent` presenta un error de infraestructura
  accionable.
- Si una herramienta falla después de iniciar por una causa de infraestructura,
  `EvaluatorAgent` marca la evaluación `INCOMPLETE_INFRASTRUCTURE`; no asigna
  cero, no renormaliza silenciosamente los pesos y no publica nota final completa.
  Se puede reintentar el análisis cuando la infraestructura esté disponible,
  conservando el snapshot y la trazabilidad.
- `ISSUES_FOUND` es un resultado válido de análisis, no un error de ejecución.
  Sus hallazgos sí alimentan la puntuación determinista.
- No se ejecuta `ktlintFormat`, `detekt --auto-correct` ni ninguna tarea que
  reescriba código durante la evaluación. Solo tareas de análisis/check.

## Evidencia y auditoría

Cada herramienta produce `ToolExecutionEvidence` con: `tool_id`, versión,
versión de runtime relevante, coordenadas/checksum, comando/tarea, módulo,
variante, cwd/workspace, timestamps, exit code, estado, health check, rutas y
hashes de reportes, stdout/stderr resumidos, causa de error y `project_snapshot_hash`.
El reporte R9 debe mostrar estado de preparación y ejecución por separado.

## Requisitos adicionales

- **RQ-EXM-064 — ToolchainManager:** servicio determinista responsable de detectar,
  resolver, instalar/configurar de forma aislada y verificar herramientas.
- **RQ-EXM-065 — Herramientas estáticas obligatorias:** Android Lint, Detekt y
  KtLint son requeridas para completar D3; ninguna puede omitirse silenciosamente.
- **RQ-EXM-066 — Matriz de compatibilidad fijada:** versiones provienen de
  `toolchain-policy.json`; prohibido usar `latest` o resolver versiones
  indeterminadas en una evaluación reproducible.
- **RQ-EXM-067 — Preflight de toolchain:** las tres herramientas deben estar
  `READY` antes de crear el intento/iniciar el timer.
- **RQ-EXM-068 — Instalación aislada:** no instalar globalmente ni alterar
  permanentemente el proyecto original; usar caché ADA Sensei y workspace temporal.
- **RQ-EXM-069 — Health check real:** confirmar ejecución real y reporte válido,
  no solo presencia de plugin/tarea/binario.
- **RQ-EXM-070 — Fallo de preparación bloqueante:** si una herramienta no puede
  prepararse, no iniciar el examen y devolver error de infraestructura.
- **RQ-EXM-071 — Fallo durante evaluación:** marcar `INCOMPLETE_INFRASTRUCTURE`,
  preservar evidencias y no emitir nota final completa ni convertirlo en cero.
- **RQ-EXM-072 — No mutación del código:** prohibir tareas de autoformato/fix y
  comprobar que el hash del proyecto original no cambió.
- **RQ-EXM-073 — Manifiesto reproducible:** persistir `ToolchainManifest` con
  versiones, checksums, comandos, módulos/variantes y hashes de reportes.
- **RQ-EXM-074 — TeacherAgent no administra herramientas:** TeacherAgent solo
  muestra los estados y comunica causas; la preparación y verificación pertenecen
  a EvaluatorAgent mediante ToolchainManager.
- **RQ-EXM-075 — Seguridad de dependencias:** permitir repositorios declarados,
  limitar ejecución de scripts y registrar origen/checksum; no ejecutar
  instaladores externos no confiables.
- **RQ-EXM-076 — Progreso visible de inicio:** abrir el panel o elegir
  `Empezar examen` no ejecuta la preparación del toolchain en el hilo de la
  interfaz. El TUI muestra de inmediato un estado localizado de preparación y
  emite mensajes por etapas reales: validación, preparación de herramientas y
  creación del intento. No hay progreso simulado y no se crea estado antes de
  que el preflight termine.

## Criterios de aceptación

1. Proyecto con las tres herramientas ya configuradas: preflight valida versiones,
   ejecuta health checks y permite iniciar.
2. Proyecto sin Detekt/KtLint: ADA Sensei prepara configuración aislada, ejecuta
   ambas herramientas y no modifica el árbol original.
3. Android Lint disponible vía AGP: se ejecuta la tarea correcta para la variante.
4. Versión incompatible: se intenta resolver una combinación fijada soportada;
   si no existe, se bloquea con `INCOMPATIBLE`.
5. Sin red/cache/permisos: preflight bloquea el inicio, sin intento ni timer.
6. Error de herramienta durante evaluación: no hay cero ni nota final completa.
7. Hallazgos reales: estado `ISSUES_FOUND`, hallazgos visibles y puntuación
   calculada con la regla D3.
8. Mismo snapshot, toolchain manifest y ruleset producen evidencias reproducibles
   dentro de los límites documentados de cada herramienta.
9. El hash del proyecto original antes/después es idéntico.
10. TeacherAgent no puede invocar instalación ni modificar estados/puntuaciones.
11. El panel muestra "Preparando…" antes de la validación pesada, emite avances
    reales por etapa y no crea el intento hasta que el preflight termina.


## Adenda v2 — Reporte y evaluación LLM

### RQ-EXM-078 Evaluación funcional asistida por LLM
Cada criterio de aceptación del JSON SHALL recibir una decisión semántica estructurada del modelo configurado, sustentada en evidencia concreta.

### RQ-EXM-079 Clean Architecture y MVVM
La dimensión de arquitectura SHALL evaluar Clean Architecture y MVVM por separado, con igual peso interno y evidencias de dependencias, responsabilidades y pruebas.

### RQ-EXM-080 Reporte oficial único
Por intento SHALL existir un único EvaluationReport consumido por TUI, persistencia y PDF. Una reevaluación debe crear una revisión vinculada, no una nota paralela.

### RQ-EXM-081 PDF auditable
El PDF SHALL mostrar por requisito/criterio estado, explicación breve y evidencia con ruta y líneas cuando existan; incluir desglose de arquitectura y limitaciones.

### RQ-EXM-082 Consistencia numérica
Resumen, tablas y conclusión SHALL derivarse del mismo desglose y coincidir en notas, pesos, contribuciones y cobertura.

### RQ-EXM-083 Cobertura parcial
Si hay criterios no evaluados o fallos del LLM/toolchain, el PDF SHALL declarar evaluación parcial y mostrar peso excluido; nunca convertir indisponibilidad en cero.

### RQ-EXM-084 Hallazgos priorizados
El PDF SHALL mostrar un máximo de cinco acciones prioritarias vinculadas a criterios o hallazgos, y agrupar el resto sin saturar el documento.

### RQ-EXM-085 Contrato exacto de interpretación del examen
`ExamInterpretationAgent` SHALL solicitar y validar un objeto con `strengths`,
`weaknesses`, `recommendations`, `findings`, `feedback`,
`next_learning_activity`, `limitations` y `architecture`. Cada objeto de
`strengths`, `weaknesses`, `recommendations`, `findings` y `architecture` SHALL
incluir `claim`, `evidence_refs` y `kind`; se prohíben alias como `description`,
`text`, `title` o `summary`, campos adicionales y respuestas vacías. Una salida
inválida SHALL registrarse como limitación explícita sin alterar la puntuación
determinista ni fabricar evidencia.

---

# Adenda normativa — Recursos de examen multiplataforma (2026-11-25)

Prevalece sobre RQ-EXM-035 y sobre cualquier sección anterior que use
`instructions_path` como definición JSON. La base de esta decisión es ADR-030.

- **RQ-EXM-086 — Recursos separados:** `instructions_path`,
  `exam_definition_path` y `project_path` son configuraciones independientes.
  Ningún cargador puede utilizar el valor de otro recurso.
- **RQ-EXM-087 — Instrucciones:** `/instructions <ruta>` acepta solo un archivo
  Markdown regular, legible y no vacío con extensión `.md`. Rechaza una
  definición de examen JSON con un error explícito de tipo de recurso.
- **RQ-EXM-088 — Definición:** `/exam-definition <ruta>` y
  `exam-init <ruta.json>` aceptan solo una definición JSON existente, regular,
  legible, válida según el esquema y con semántica válida.
- **RQ-EXM-089 — Resolución centralizada:** `ResourceResolver` expande `~`,
  respeta rutas absolutas, resuelve relativas contra un directorio base
  documentado, comprueba existencia/tipo/permisos y nunca cambia una ruta
  inválida por otra sin declararlo.
- **RQ-EXM-090 — Persistencia:** las referencias se guardan relativas al
  directorio base cuando es posible. Una referencia absoluta o con base de otro
  sistema se valida al cargar; si ya no existe, se informa sin reutilizarla.
- **RQ-EXM-091 — Migración:** una sesión heredada cuya definición JSON válida
  estuviera en `instructions_path` se migra explícitamente a
  `exam_definition_path`; una ruta inválida no se convierte en instrucciones.
- **RQ-EXM-092 — Empaquetado:** los recursos internos (instrucciones, schema,
  configuración de learning path y política de toolchain) se incluyen en la
  distribución y se localizan con `importlib.resources` cuando corresponda.
- **RQ-EXM-093 — Errores:** todo error incluye el recurso, la ruta resuelta y
  la razón concreta. El panel de preparación muestra y valida ambos recursos.

---

# Adenda normativa — Comando único `/instructions` (2026-11-25)

Prevalece sobre RQ-EXM-086 a RQ-EXM-093 en todo lo relativo a la interfaz de
configuración. La base de esta decisión es ADR-031.

- **RQ-EXM-094 — Comando único:** `/instructions <ruta>` SHALL ser el único
  comando visible para configurar o mostrar la definición JSON del examen.
  SHALL validar existencia, tipo regular, legibilidad, esquema y semántica.
- **RQ-EXM-095 — Retiro de `/exam-definition`:** `/exam-definition` SHALL NO
  existir en el parser, router, ayuda, registro de acciones ni TUI.
- **RQ-EXM-096 — Fuente interna:** `exam_definition_path` SHALL seguir siendo
  la fuente autoritativa. `instructions_path` SHALL tratarse solo como campo
  heredado de sesión y SHALL NO validarse como Markdown.
- **RQ-EXM-097 — Preparación:** el preflight SHALL requerir una definición JSON
  válida configurada con `/instructions`; SHALL NO requerir instrucciones
  Markdown independientes.
- **RQ-EXM-098 — Conservación:** RQ-EXM-089 a RQ-EXM-093 SHALL conservarse en
  resolución, persistencia, migración, empaquetado y errores.

---

# Adenda normativa — PDF paginado y reintento (2026-11-26)

- **RQ-EXM-099 — Paginación adaptativa:** el PDF SHALL ocupar tantas páginas
  como requiera el contenido de `EvaluationReport`, sin límite fijo, sin
  eliminar secciones obligatorias ni evidencias, sin páginas vacías o contenido
  cortado y con numeración de páginas.
- **RQ-EXM-100 — Persistencia anterior al PDF:** `ExamineAction.finish()`
  SHALL persistir el `EvaluationReport` antes de generar el PDF. Un fallo de
  generación SHALL conservar el reporte, marcar la evaluación como terminada y
  registrar el error; un éxito SHALL registrar la ruta del PDF y su estado.
- **RQ-EXM-101 — Reintento PDF:** la operación de reintento SHALL recuperar el
  mismo `EvaluationReport` persistido y regenerar el PDF conservando
  `evaluation_id`, sin crear otro `ExamAttempt`, sin ejecutar herramientas o
  modelo, sin recalcular la nota y sin duplicar resultados persistidos. Si el
  reporte no existe o está incompleto, SHALL informar el problema sin iniciar
  otra evaluación automáticamente.
