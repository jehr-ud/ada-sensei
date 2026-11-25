# Tareas — 007 Examine

## Estado actual

La auditoría de completitud (`IMPLEMENTATION-STATUS.md`) determina que la spec
no está completa: el motor base, el panel de inicio y el preflight real funcionan,
pero faltan partes de la adenda de informe determinista, checksums de toolchain
y el temporizador. Las casillas de este archivo están desactualizadas y deben
leerse junto con esa auditoría.

Las casillas `[x]` y `[ ]` reflejan el registro histórico de trabajo y no deben
interpretarse como estado verificado sin consultar la auditoría.

Decisiones de resolución aplicadas:
- El requisito legado `RQ-EXM-052` se renombra `RQ-EXM-052-DEBUG`; las adendas
  conservan `RQ-EXM-052`–`RQ-EXM-076`.
- `exam-default:v1` y `evaluate-default:v1` migran a `unified-android:v1` sin
  alias temporales, incluyendo persistencia y pruebas.
- La matriz `toolchain-policy.json:11-45` cubre dos combinaciones fijadas. La
  combinación Gradle 9.5.0 / Kotlin 2.2.10 / AGP 9.3.3 injecta Detekt/KtLint en
  un workspace temporal y fue verificada manualmente con reportes reales; faltan
  checksums de plugin markers y una prueba de integración automatizada en CI.

---

## 1. Motor de evaluación de exámenes ✓

- [x] `ExamDefinitionLoader` carga enunciados Markdown, JSON y PDF.
- [x] Parser Markdown reconoce **Formato A** (bullets bajo encabezados de requisitos).
- [x] Parser Markdown reconoce **Formato B** (tabla bajo encabezados de criterios,
  incluyendo encabezados numerados como `## 7. Criterios de evaluación`).
- [x] Detección de columna de peso por prioridad: `Peso funcional` sobre `Puntaje`.
- [x] Pesos en escala >1 (puntos) se normalizan a escala 0–1.
- [x] `limitations` explícitas cuando no se puede parsear una sección.
- [x] Suma de pesos funcionales validada (debe ser exactamente 1.0).
- [x] Ids de requisito estables derivados del contenido del enunciado.
- [x] `ExamLifecycle` con máquina de estados `CREATED→ACTIVE→EVALUATING→COMPLETED`.
- [x] `ExamineAction.start` / `.finish` orquesta el ciclo completo.
- [x] `ExamScorer` scoring determinista por dimensión.
- [x] `ArchitectureAnalyzer` separa observed/documented/inferred.
- [x] `ExamInterpretationAgent` pipeline LLM acotado (máximo 3 intentos).
- [x] `ExamReportGenerator` genera PDF con tabla de cálculo.

## 2. Correcciones al motor (aplicadas) ✓

- [x] **Detekt no configurado**: `StaticAnalysisTool.run_detekt` llama a
  `_detekt_not_configured` antes de registrar evidencia de fallo. Si la tarea
  no existe en el proyecto, registra `status="missing"` sin penalizar la nota.
- [x] **Manifest de debug opcional**: `AndroidProjectAnalyzer._check_optional`
  registra `app/src/debug/AndroidManifest.xml` con `status="info"` al no
  encontrarlo. `DimensionScorer._score_architecture` ignora `status="info"`.
- [x] **Normalización objeto→array en LLM**: `_coerce_array_fields` en
  `StructuredPipeline.run` envuelve un objeto solitario en lista cuando el
  campo del esquema espera un array, antes de validar el esquema.
- [x] **`DocumentationRules` con globs ampliados**: los globs predeterminados
  cubren `docs/**/*.md`, `docs/**/*.pdf`, `*.md`, `INFORME*.md`, `REPORT*.md`,
  además de `docs/exam/**/*.md`.

## 3. Persistencia, eventos, locale ✓

- [x] `ExamStore` persiste intentos, definiciones y eventos.
- [x] `ExamEventBridge` conecta el bus de eventos al intento activo.
- [x] Ask count se recalcula desde el log de eventos al finalizar.
- [x] `ExamAttempt.locale` snapshot del locale al iniciar.
- [x] `ExamResult.locale` preserva el snapshot para el informe.
- [x] `ExamPreparationService` valida precondiciones sin crear estado.

## 4. Informe PDF ✓

- [x] PDF escrito en `docs/ada-sensei/exams/<exam_id>/report.pdf` dentro del
  proyecto (RQ-EXM-024).
- [x] Tabla de cálculo reconstructible con dimensiones, pesos, puntuaciones y
  contribuciones.
- [x] `grade_disclosure` con texto `SUGGESTED_GRADE_LABEL`.
- [x] `ExamDocsWriter.write_finish_docs` agrega `architecture.md` y
  `evaluation-summary.md` al finalizar.

## 5. Pruebas automatizadas existentes ✓

- [x] `tests/exams/test_definition.py` — formatos de carga.
- [x] `tests/exams/test_integration.py` — ciclo completo start/finish.
- [x] `tests/exams/test_exams_structured_output.py` — pipeline LLM.
- [x] `tests/exams/test_exams_architecture.py` — tipos de afirmaciones.
- [x] `tests/exams/test_exams_rubric.py` — pesos y subcriteria.
- [x] `tests/exams/test_scoring.py` — scoring determinista.
- [x] `tests/exams/test_process_metrics.py` — métricas de proceso.
- [x] `tests/exams/test_ask_tracking.py` — conteo de consultas.
- [x] `tests/exams/test_lifecycle.py` — transiciones de estado.
- [x] `tests/exams/test_persistence.py` — persistencia y fallos.
- [x] `tests/exams/test_report.py` — PDF y disclosure.
- [x] `tests/exams/test_docs.py` — documentación generada y del estudiante.
- [x] `tests/exams/test_exam_locale.py` — snapshot de locale.
- [x] `tests/exams/test_duration.py` — duración y overtime.

## 6. Pruebas de regresión con Domino Conquista (pendientes)

- [ ] Test: 7 requisitos cargados desde la tabla de criterios del enunciado real.
- [ ] Test: pesos suman 1.0 (`0.20+0.20+0.20+0.10+0.10+0.15+0.05`).
- [ ] Test: `_detekt_not_configured` retorna `True` para el output real de Domino.
- [ ] Test: `AndroidProjectAnalyzer` produce `status="info"` para el manifest de debug.
- [ ] Test: `_score_architecture` no penaliza cuando solo hay `status="info"`.
- [ ] Test: `_coerce_array_fields` normaliza objeto→lista sin consumir intento.
- [ ] Test: fallo total del LLM conserva `raw_score_50` y `suggested_grade`.

## 7. TUI — panel de preparación (implementado; pendiente el temporizador)

- [x] `ExamPreparationScreen` con lista compacta (patrón `LanguageList`).
- [x] Sin botones grandes Confirmar/Cancelar.
- [x] Muestra estado de estudiante, proyecto, preflight e instrucciones.
- [x] Opciones `Empezar examen` / `Volver` con Arriba/Abajo/Enter/Escape.
- [x] Bloquea `Empezar examen` con mensaje localizado si hay precondiciones pendientes.
- [x] Muestra `Preparando…` y avances reales por etapa sin bloquear la interfaz (RQ-EXM-076).
- [ ] Permite escribir `/project` y `/instructions` y actualiza el panel.
- [ ] Abrir/cancelar el panel no crea side effects.

## 8. Comandos `/project` e `/instructions` (parcialmente implementado)

- [x] `/project <ruta>` actualiza `SessionContext` y el campo canónico existente.
- [ ] `/instructions <ruta>` al registro/parser compartido.
- [ ] Validar extensión `.md`, archivo regular, legible y no vacío.
- [ ] Guardar ruta en `SessionContext.instructions_path`.
- [ ] Ayuda bilingüe en `/help`.
- [ ] Pruebas: rutas absolutas/relativas/`~`, cwd no cambia.

## 9. Temporizador TUI (pendiente)

- [ ] Indicador compacto persistente durante el examen activo.
- [ ] Elapsed `HH:MM:SS`.
- [ ] Remaining si `allowed_duration_seconds` está definido.
- [ ] Aviso localizado al alcanzar cero, sin auto-finalizar.
- [ ] Contador `/ask` y límite si existe.
- [ ] Scheduler no bloqueante del TUI.
- [ ] Reconstrucción desde `started_at` al reanudar.

## 10. Finalización TUI (pendiente)

- [ ] Confirmación compacta `Finalizar examen` / `Continuar` sin botones grandes.
- [ ] Mensajes de progreso por etapa durante la finalización (RQ-EXM-048).
- [ ] Apertura best-effort del PDF con `tools.open_report` (RQ-EXM-049).

## 11. CLI no interactivo (pendiente)

- [ ] `exam-init --yes` ejecuta `ProjectPreflight` completo antes de crear estado.
- [ ] Integración de `/instructions` en el parser/router CLI.

## Definición de terminado

- [x] Los requisitos RQ-EXM-001 a RQ-EXM-031, RQ-EXM-044 a RQ-EXM-050 tienen
  pruebas automatizadas que pasan.
- [x] Los 7 requisitos del examen Domino Conquista se cargan con pesos correctos.
- [x] Un examen Domino Conquista completo produce `raw_score_50` y `suggested_grade`
  sin errores de schema LLM ni penalizaciones injustificadas.
- [ ] Los requisitos TUI (RQ-EXM-033, 039–043, 047–049) tienen pruebas de widget.
- [x] No hay botones grandes Confirmar/Cancelar en el inicio de examen.
- [ ] El temporizador se muestra y es reconstruible desde el timestamp persistido.
- [ ] No se ha duplicado parser, preflight, loader, lifecycle, scoring ni
  persistencia.


---

# Tareas nuevas — Reporte determinista y EvaluatorAgent (2026-11-20)

## A. Agentes y contratos
- [ ] Definir `EvaluatorAgent` como único evaluador y productor de `EvaluationReport`.
- [ ] Integrar `TeacherAgent` como consumidor del reporte; prohibir scoring en TeacherAgent.
- [ ] Crear modelos Pydantic: `EvaluationReport`, `DimensionResult`, `CriterionResult`,
      `Finding`, `EvidenceReference`, `ToolRun`, `AnalyzerCoverage`, `CalculationTrace`.
- [ ] Añadir versionado de rúbrica y rulesets; preservar compatibilidad/migración.

## B. Rúbrica única
- [ ] Sustituir `exam-default:v1` y la rúbrica divergente de `/evaluate` por
      rúbrica unificada versionada 40/20/15/15/10.
- [ ] Configurar Detekt 40%, Android Lint 35%, KtLint 25% dentro de D3.
- [ ] Configurar subcriterios MVVM M1–M5 y pesos 30/25/20/15/10.
- [ ] Configurar subcriterios Android A1–A7 y pesos 15/20/10/15/15/15/10.
- [ ] Asegurar que no se use Clean Architecture como dimensión.

## C. Análisis determinista
- [ ] Implementar D1 con trazabilidad requisito-caso-evidencia.
- [ ] Implementar D2 con umbral del 80% de requisitos cubiertos y fórmulas T1/T2/T3.
- [ ] Normalizar severidades y hallazgos de Detekt, Android Lint y KtLint.
- [ ] Implementar analizador MVVM basado en imports, dependencias, estado y pruebas.
- [ ] Implementar los siete subcriterios de buenas prácticas Android.
- [ ] Implementar estados PASS/PARTIAL/FAIL/NOT_EVALUATED/NOT_CONFIGURED/
      NOT_AVAILABLE/EXECUTION_ERROR/INFO.
- [ ] Garantizar que errores de infraestructura no penalicen al estudiante.

## D. PDF determinista
- [ ] Rediseñar `ExamReportGenerator` para producir las tablas R1–R12.
- [ ] Generar PDF de máximo 4 páginas, sin narrativa libre LLM.
- [ ] Crear catálogo de observaciones/recomendaciones `es-CO` y `en-US`.
- [ ] Incluir hallazgos con IDs, severidad, archivo/línea y evidencia.
- [ ] Mostrar las cinco dimensiones siempre, incluyendo no evaluadas.
- [ ] Incluir cobertura, cálculo reproducible, versión de reglas y limitaciones.
- [ ] Generar el PDF solo desde `EvaluationReport`.

## E. TeacherAgent
- [ ] TeacherAgent invoca EvaluatorAgent y consume `EvaluationReport`.
- [ ] TeacherAgent no ejecuta scoring ni cambia estados/notas.
- [ ] Explicaciones pedagógicas referencian finding_id/criterion_id/evidence_id.
- [ ] Verificar que las respuestas del TeacherAgent no modifican el PDF.

## F. Pruebas
- [ ] Pruebas unitarias de cada fórmula y cada regla de tabla D1–D5.
- [ ] Pruebas de límites 79.99%, 80%, 100% en cobertura de requisitos.
- [ ] Pruebas de hallazgos por severidad y deduplicación.
- [ ] Pruebas de MVVM con falsos positivos/negativos conocidos.
- [ ] Pruebas de aplicabilidad y exclusión de indicadores Android.
- [ ] Pruebas de estabilidad: mismas evidencias/ruleset => mismos scores.
- [ ] Pruebas que demuestren que LLM no puede alterar notas ni estados.
- [ ] Pruebas de PDF para tablas R1–R12 y ausencia de narrativa LLM.
- [ ] Pruebas de integración EvaluatorAgent → TeacherAgent.
- [ ] Regresión con Domino Conquista y fixture de proyecto Android real.

## Definición de terminado
- [ ] Las cinco dimensiones se evalúan por EvaluatorAgent con evidencia rastreable.
- [ ] TeacherAgent usa el reporte y no evalúa por cuenta propia.
- [ ] La misma rúbrica versionada se utiliza en `/evaluate` y `/exam`.
- [ ] El PDF se genera sin llamadas LLM y todas sus tablas tienen reglas testeadas.
- [ ] No se declara `COMPLETE` cuando falta evidencia requerida.


## 9. Definición estructurada JSON obligatoria

- [ ] Sustituir la carga autoritativa Markdown/PDF por JSON exclusivamente (RQ-EXM-052).
- [ ] Implementar validación con `exam-definition.schema.json` y validaciones semánticas (RQ-EXM-053–057).
- [ ] Crear ejemplo Domino Conquista y validar pesos/IDs/criterios (RQ-EXM-054–056).
- [ ] Guardar snapshot inmutable y SHA-256 de la definición en `ExamAttempt` (RQ-EXM-058).
- [ ] Mostrar errores JSON Pointer en preparación y bloquear el inicio (RQ-EXM-059).
- [ ] Asegurar que TeacherAgent solo coordine y EvaluatorAgent sea el único evaluador (RQ-EXM-060–061).
- [ ] Reportar hallazgos no mapeados sin afectar la nota (RQ-EXM-062).
- [ ] Implementar registro de métodos de verificación y estados de disponibilidad (RQ-EXM-063).
- [ ] Pruebas: JSON válido/inválido, pesos, IDs duplicados, snapshot/hash, no autocorrección LLM y separación de agentes.


## 10. Preparación automática de herramientas estáticas (RQ-EXM-064–075)

- [x] Implementar `ToolchainManager` como servicio determinista invocado por `EvaluatorAgent`.
- [x] Crear loader/validador de `toolchain-policy.json`; rechazar versiones flotantes y combinaciones no verificadas.
- [x] Detectar JDK, Gradle wrapper, Kotlin, AGP, módulos, variantes y tareas Android Lint.
- [x] Resolver Detekt y KtLint con versiones fijadas y compatibles; Android Lint se resuelve desde AGP.
- [x] Implementar caché aislada ADA Sensei y resultados repetibles; los checksums
  de plugin markers siguen pendientes.
- [x] Implementar workspace temporal/copia para configuración; no modificar proyecto original.
- [x] Ejecutar health check real de Android Lint, Detekt y KtLint y validar reportes estructurados.
- [x] Integrar preflight: bloquear antes de `ExamAttempt`/timer si cualquier herramienta requerida no queda `READY`.
- [x] Añadir estados `READY`, `INSTALLED`, `CONFIGURED`, `ISSUES_FOUND`, `NOT_CONFIGURED`, `NOT_AVAILABLE`, `INCOMPATIBLE`, `EXECUTION_ERROR`.
- [x] Persistir `ToolchainManifest` y `ToolExecutionEvidence` en el intento/reporte.
- [x] Detectar y bloquear tareas de auto-fix/format durante evaluación.
- [x] Comprobar hash del proyecto original antes/después.
- [x] Implementar `INCOMPLETE_INFRASTRUCTURE` si falla herramienta tras iniciar; no emitir nota completa.
- [x] Hacer que TeacherAgent solo comunique estados, sin instalar ni alterar calificaciones.
- [x] Pruebas: proyecto preconfigurado, faltan Detekt/KtLint, AGP sin Lint, versión incompatible, offline, fallo de health check, mutación cero, caché/checksum y reproducibilidad.
- [ ] Automatizar en CI las pruebas de integración en proyectos Android
  representativos; la estrategia de inyección temporal ya fue verificada
  manualmente en un proyecto Gradle 9.5.0, pero no se asume compatibilidad
  universal de init scripts.

Evidencia: `tests/toolchain/test_manager.py`, `tests/toolchain/test_models.py`, `tests/exams/test_toolchain_integration.py`, `tests/agents/test_teacher_agent.py`; suite completa `674 passed`; ruff enfocado limpio. `ruff check . --fix` mantiene 70 errores preexistentes fuera del alcance de este cambio. La matriz de compatibilidad contiene dos combinaciones fijadas; falta automatizar en CI la verificación con Gradle real y registrar checksums de plugin markers.


## 9. Report v2 — evaluación única, evidencia y arquitectura

- [x] Consume exclusivamente el `EvaluationReport` persistido/validado.
- [x] Elimina cálculos duplicados en `ExamReportGenerator` y plantillas.
- [x] Presenta identificación, nota, cobertura y desglose por dimensión.
- [x] Presenta cada requisito y criterio con estado, justificación y evidencia `ruta:líneas`.
- [x] Presenta Clean Architecture y MVVM como apartados separados.
- [x] Incluye hallazgos relevantes de pruebas y analizadores sin volcar reportes completos.
- [x] Muestra limitaciones, peso excluido y estado de evaluación parcial.
- [x] Limita acciones prioritarias a cinco y las vincula a IDs.
- [x] Evita tablas vacías, placeholders y filas partidas entre páginas.
- [x] Añade pruebas de consistencia entre JSON del reporte, TUI y PDF.
- [x] Ajusta el prompt y el esquema de `ExamInterpretationAgent` al contrato exacto de `claim`, `evidence_refs`, `kind` y `architecture` (RQ-EXM-085).
- [ ] Añade fixture de regresión con el PDF de Domino Conquista que detecte discrepancias de nota y evidencia.

## 10. Recursos de examen multiplataforma (ADR-030)

- [x] Añadir ADR-030 y adendas normativas en spec/requirements/design.
- [x] Implementar `ResourceResolver`, `ResourceReference` y errores tipados.
- [x] Añadir `InstructionsLoader` y rechazo de definiciones JSON como instrucciones.
- [x] Separar `instructions_path` de `exam_definition_path` en sesión, router,
     PreparationService, TUI y `ExamineAction`.
- [x] Persistir referencias relativas y migrar sesiones heredadas válidas.
- [x] Incluir recursos internos en el paquete y resolverlos con `importlib.resources`.
- [x] Añadir pruebas de rutas, confusión de recursos, permisos, Unicode, `~`,
      otra plataforma, pip y regresión del flujo de examen.
- [x] Ejecutar pytest completo, Ruff y verificación de empaquetado.
- Evidencia multiplataforma: pytest completo ejecutado en macOS; Windows se cubre
  con pruebas de rutas absolutas foráneas y `pathlib`. No se ejecutó Linux ni
  Windows reales: el daemon de Docker no está disponible en este entorno y no
  hay host Windows. El resolver no usa separadores ni rutas absolutas de un SO.

## 11. Comando único `/instructions` (ADR-031)

- [x] Añadir ADR-031 y adendas normativas en spec/requirements/design.
- [x] Hacer que `/instructions <path.json>` valide y configure la definición.
- [x] Eliminar `/exam-definition` de parser, router, ayuda y TUI.
- [x] Quitar la validación de instrucciones Markdown del preflight.
- [x] Actualizar pruebas y resultado de verificación.
- Evidencia: pytest completo 743 passed; Ruff sin hallazgos nuevos (69
  preexistentes); wheel construido e instalado con recursos y superficie de
  comandos verificados.
