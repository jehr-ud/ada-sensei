# Estado de implementación y completitud — Spec 007 Examine

- Fecha de la auditoría: 2026-11-23
- Alcance: `specs/007-examine/` (spec, requirements, design, tasks, ADR, schema,
  política de toolchain) frente al código y las pruebas presentes en el repositorio.
- Método: lectura de la normativa y sus adendas, inventario estático del código,
  trazabilidad de `RQ-EXM-*` y ejecución real de `pytest` y Ruff.
- Este documento es un informe de estado. No modifica la normativa: cuando hay
  conflicto entre secciones se aplica la precedencia declarada por las propias
  adendas.

## 1. Veredicto

**La especificación 007 NO está completa.**

El núcleo operativo del examen sí está implementado y probado (ciclo de vida,
definición JSON, métricas de proceso, persistencia, locale, preflight, rúbrica
unificada y toolchain a nivel de unidad). Sin embargo, la adenda normativa de
informe determinista y la adenda de toolchain están solo parcialmente
materializadas, y el propio paquete documental es internamente contradictorio.
No se puede declarar `COMPLETE` ni «evaluación integral» con el estado actual.

| Capa | Estado | Base de la valoración |
|---|---|---|
| Flujo base de examen (RQ-EXM-001–031, 044–051) | Completo con observaciones | `tests/exams/` y `tests/cli/`; brechas documentales y de pruebas menores |
| Definición JSON obligatoria (RQ-EXM-052–063) | Casi completo | Loader, schema, JSON Pointer, snapshot/hash; faltan verificadores y `unmapped_observations` |
| Rúbrica unificada 40/20/15/15/10 | Completa en datos, parcial en análisis | `ada_sensei/evaluation/rubric.py:182-423`; subcriterios solo declarados |
| Informe determinista y contrato EvaluatorAgent | Parcial | `EvaluationReport` y R1–R12 existen, pero el contrato `evaluate()` no y el PDF no es exclusivo del reporte tipado |
| Toolchain estático (RQ-EXM-064–075) | Parcial | Dos combinaciones fijadas (`toolchain-policy.json:11-45`), auto-configuración aislada con init scripts (`manager.py:286-365`) y health checks reales verificados en proyecto Android Gradle 9.5; faltan checksums de artefactos |
| TUI de preparación, temporizador y finalización | Parcial | Existen widget compacto, sin botones grandes, y footer de examen; faltan temporizador y pruebas de widget adicionales |
| Documentación de la spec y trazabilidad | Incompleta | Textos base contradichos por adendas; `requirements.md:277-320` y `tasks.md` desactualizados |

## 2. Precedencia normativa y contradicciones detectadas

Las adendas declaran expresamente que prevalecen sobre las secciones anteriores
(`requirements.md:326-334`, `:831-838`, `:893-899`; `design.md:782-784`,
`:830-836`; `spec.md:413-421`, `:918-920`, `:959-965`).

| Tema | Texto base | Norma prevaleciente | Implementación real | Pendiente documental |
|---|---|---|---|---|
| Fuente de requisitos | Markdown, JSON y PDF (`requirements.md:7-26`, `spec.md:88-153`) | Solo `.json` validado (RQ-EXM-052, `requirements.md:879`) | Solo JSON (`exams/definition.py:58-95`) | Corregir RQ-EXM-002, RQ-EXM-035, `tasks.md:21-25` y textos de ayuda |
| Rúbrica | `exam-default:v1` 40/15/15/15/5/10 (`requirements.md:109-112`) | `unified-android:v1` 40/20/15/15/10 | Migrada sin alias (`evaluation/rubric.py:182-196`, `:399-404`) | Corregir `spec.md:315-339` y RQ-EXM-018 |
| D4 | `clean_architecture` (RQ-EXM-014) | MVVM M1–M5, sin Clean Architecture | Pesos MVVM presentes, pero queda sección «Clean architecture» en el PDF (`exams/report.py:229-232`) | Marcar RQ-EXM-014 como superada y eliminar la sección heredada |
| `/instructions` | Extensión `.md` (RQ-EXM-035, ADR-026:18) | Definición JSON del docente | Exige `.json` (`cli/router.py:524-544`, `exams/preparation.py:138-139`) | Actualizar RQ-EXM-035, ADR-026 y cadenas de ayuda (`cli/tui/app.py:87,100`) |
| Estado de ADR | Propuesto (ADR-026:4, ADR-027:4, ADR-028:3) | — | Decisiones parcialmente implementadas | Consolidar estado real de cada ADR |
| Tareas | Casillas `[x]`/`[ ]` mezcladas | — | Varias casillas no reflejan el código actual | Regenerar `tasks.md` a partir de esta auditoría |

El código también conserva superficies heredadas coherentes con el texto base
pero no con las adendas: `cli/action_registry.py:133-146` anuncia Markdown/PDF,
`exams/pdftext.py` y su exportación en `exams/__init__.py:46` permanecen, y
`exams/preparation.py:139` usa el código de bloqueo `instructions_not_markdown`
para un archivo que en realidad debe ser `.json`.

## 3. Trazabilidad de requisitos

Leyenda: `OK` = implementado y con prueba automatizada; `PARCIAL` = implementado
pero sin prueba suficiente o con desviación parcial; `FALTA` = no implementado;
`SUPERADA` = reemplazada por una adenda; `BLOQUEADO` = mecanismo presente pero
inutilizable con la configuración entregada.

### 3.1 Requisitos base

| Requisito | Estado | Evidencia / observación |
|---|---|---|
| RQ-EXM-001 identidades separadas | OK | `tests/exams/test_exams_models.py:14-52` |
| RQ-EXM-002 formatos Markdown/JSON/PDF | SUPERADA | Prevalece RQ-EXM-052 (JSON único) |
| RQ-EXM-003 inicio transaccional | OK | `tests/exams/test_lifecycle.py:18`, `test_integration.py:69` |
| RQ-EXM-004 finalización e inmutabilidad | OK | `tests/exams/test_lifecycle.py:50`, `exams/store.py:39-65` |
| RQ-EXM-005 conteo de `/ask` | OK | `tests/exams/test_ask_tracking.py:42-196` |
| RQ-EXM-006 historial de eventos | OK | `tests/exams/test_ask_tracking.py:65`; `exams/events.py:52-77` |
| RQ-EXM-007 duración autoritativa | OK | `tests/exams/test_duration.py:15-33`; `exams/lifecycle.py:173` |
| RQ-EXM-008 globs de documentación | OK | `tests/exams/test_docs.py:19` |
| RQ-EXM-009 documentación generada | OK | `tests/exams/test_docs.py:51` |
| RQ-EXM-010 reutilización del pipeline | OK | `tests/exams/test_integration.py:30-60` |
| RQ-EXM-011 sin instrumentadas | OK | `tests/exams/test_integration.py:40` |
| RQ-EXM-012 requisitos funcionales | PARCIAL | Enlace y peso correctos, pero el ejemplo Domino tiene 3 requisitos (2 funcionales), no los 7 declarados en `tasks.md:90-91` |
| RQ-EXM-013 calidad determinista | PARCIAL | Score determinista probado; D3 no puntúa Detekt/Lint/KtLint por separado |
| RQ-EXM-014 arquitectura limpia | SUPERADA | La adenda D4 exige MVVM |
| RQ-EXM-015 pruebas no disponibles | OK | `tests/exams/test_scoring.py:70` |
| RQ-EXM-016 prácticas Android | PARCIAL | Score agregado probado; A1–A7 no se evalúan individualmente |
| RQ-EXM-017 rúbrica de proceso | OK | `tests/exams/test_process_metrics.py:16-39` |
| RQ-EXM-018 pesos `exam-default:v1` | SUPERADA | Migración a `unified-android:v1` |
| RQ-EXM-019–022 scoring y evidencia | OK | `tests/exams/test_scoring.py:107-165` |
| RQ-EXM-023, 030 afirmaciones fundamentadas | OK | `tests/exams/test_exams_architecture.py:52-83` |
| RQ-EXM-024 PDF dentro del proyecto | OK | `tests/exams/test_report.py:56`, `tests/cli/test_exam_flow.py:184` |
| RQ-EXM-025 normalización objeto→array | PARCIAL | Existe `_coerce_array_fields` (`llm/pipeline.py:82,103`); sin prueba dedicada |
| RQ-EXM-026–029 persistencia, historial, integridad, etiqueta de nota | OK | `tests/exams/test_persistence.py`, `test_report.py:89` |
| RQ-EXM-031 integridad de métricas | OK | `tests/exams/test_ask_tracking.py:87`, `cli/router.py:356-385` |
| RQ-EXM-032 preflight | OK | `tests/evaluation/test_preflight.py:69-105` |
| RQ-EXM-033 panel de preparación TUI | OK | `cli/tui/widgets.py:359-491` + `cli/tui/app.py:1209-1248`; `tests/cli/tui/test_exam_confirmation.py`, `test_exam_preparation_panel.py` |
| RQ-EXM-034 `/project` | OK | `tests/cli/test_project_command.py:21`, `cli/router.py:501-515` |
| RQ-EXM-035 `/instructions` `.md` | SUPERADA / PARCIAL | Implementado como `.json` según adenda; sin pruebas de rutas ni validación |
| RQ-EXM-036–038 bloqueos, revalidación, confirmación | OK | Guía localizada en el log desde `app.py:1223-1248`; revalidación en `app.py:1385-1392` y `actions/examine.py:253-279`; pruebas TUI de inicio bloqueado/listo |
| RQ-EXM-039–041 temporizador y contador TUI | PARCIAL | Footer y `set_interval` reales (`cli/tui/widgets.py:66-107`, `app.py:400-419`); sin pruebas de widget |
| RQ-EXM-042 aviso al agotar tiempo | PARCIAL | El restante se fija en 0, pero no hay aviso localizado de vencimiento; no hay auto-finalización |
| RQ-EXM-043 configuración inmutable del intento | PARCIAL | El intento guarda su propio `project_id`; sin prueba dedicada |
| RQ-EXM-044 CLI `--yes` | PARCIAL | Parser y preflight por separado; sin prueba que los integre antes del intento |
| RQ-EXM-045–046 locale y compatibilidad | OK | `tests/exams/test_exam_locale.py:132-153` |
| RQ-EXM-047 finalización compacta | OK | `ExamPreparationList.show_finish` en `cli/tui/widgets.py:406-444`, abierta desde `app.py:1258-1264`; sin barra en el flujo de examen |
| RQ-EXM-048 progreso de finalización | PARCIAL | Probado en CLI (`tests/cli/test_exam_flow.py:203`); cobertura TUI no verificada |
| RQ-EXM-049–050 apertura y ruta del PDF | OK | `tests/cli/tui/test_exam_preparation_panel.py:102-114`, `tools/opener.py:15-41` |
| RQ-EXM-051 Detekt no configurado | PARCIAL | `_detekt_not_configured` existe (`evaluation/evidence.py:282,369`); sin prueba |
| RQ-EXM-052-DEBUG manifest debug opcional | PARCIAL | `evaluation/evidence.py:54,79-80`; sin prueba |

### 3.2 Adenda de informe determinista y definición JSON

| Requisito / regla | Estado | Evidencia / observación |
|---|---|---|
| Agente único evaluador con `evaluate(request) -> EvaluationReport` | FALTA | No existe ese método; hay `EvaluatorAgent.build_report(...)` (`evaluation/exam_agent.py:57-74`) y `EvaluationEngine.evaluate(...)` |
| TeacherAgent consume el reporte, no puntúa | PARCIAL | `agents/teacher.py:357-381`; no invoca al evaluador; prueba débil en `tests/agents/test_teacher_agent.py:310` |
| Contrato Pydantic `EvaluationReport` | OK | `evaluation/models.py:334-381`; valida estados no evaluables |
| Cinco dimensiones y pesos 40/20/15/15/10 | OK | `evaluation/rubric.py:200-383`; `tests/exams/test_exams_rubric.py:10-18` |
| D1: criterios y fórmula por requisito | PARCIAL | Pesos y resultados proyectados; sin evaluador de casos de aceptación por requisito |
| D2: T1/T2/T3 y umbral 80% | PARCIAL | Declarados y mostrados (`exam_agent.py:344-389`); no calculan la nota de la dimensión |
| D3: Detekt 40 / Lint 35 / KtLint 25 y severidades | PARCIAL | Pesos declarados (`rubric.py:241-263`); sin normalización de severidades ni deduplicación probadas |
| D4: M1–M5 con análisis de imports/estado | PARCIAL | Subcriterios declarados (`rubric.py:269-312`); el reporte copia la nota de dimensión a cada uno (`exam_agent.py:254-278`) |
| D5: A1–A7 e indicadores | PARCIAL | Subcriterios declarados (`rubric.py:318-382`); sin analizador por indicador |
| Estados PASS/PARTIAL/FAIL/NOT_* /INFO | PARCIAL | Enumeración disponible (`evaluation/models.py:160-185`); cobertura de reglas incompleta |
| `AnalyzerCoverage` por dimensión | PARCIAL | Proyección simple en `exam_agent.py:100-102` |
| PDF solo desde `EvaluationReport`, sin prosa LLM, máximo 4 páginas | FALTA | `exams/report.py:58-59,122-137,221-258` sigue renderizando `ExamResult` con secciones narrativas y «Clean architecture» |
| Tablas R1–R12 | PARCIAL | Secciones y renderizado tipado (`report.py:262-279`); las pruebas solo verifican encabezados (`tests/exams/test_evaluation_report.py:78-102`) |
| Catálogo de observaciones/recomendaciones localizado | PARCIAL | Observaciones derivadas de hallazgos; sin catálogo versionado completo ni pruebas de plantillas |
| Bloqueo de LLM para notas/estados/PDF | PARCIAL | Scoring determinista probado; el PDF hereda campos narrativos del LLM |
| RQ-EXM-052–057 JSON, schema, pesos, `rubric_ref` | OK | `tests/exams/test_definition.py:94-282`, `exam-definition.schema.json` |
| RQ-EXM-058 snapshot y SHA-256 en el intento | PARCIAL | Snapshot/hash en `ExamDefinition` (`definition.py:330-331`) persistida por `store.py:125-137`; los campos de `ExamAttempt` (`models.py:215-216`) no se poblan y no hay prueba de persistencia en el intento |
| RQ-EXM-059 errores con JSON Pointer | OK | `tests/exams/test_definition.py:154-222` |
| RQ-EXM-060–061 separación de agentes | PARCIAL | No hay integración EvaluatorAgent→TeacherAgent ni prueba de prohibición de rescoring |
| RQ-EXM-062 `unmapped_observations` | FALTA | No existe en `ada_sensei/exams/` ni en el contrato tipado |
| RQ-EXM-063 métodos de verificación y `NOT_AVAILABLE` | PARCIAL | Métodos validados (`definition.py:267-274`); no hay registro de verificadores |

### 3.3 Adenda de toolchain

| Requisito | Estado | Evidencia / observación |
|---|---|---|
| RQ-EXM-064 `ToolchainManager` determinista | OK | `toolchain/manager.py:167-261`; `tests/toolchain/test_manager.py` |
| RQ-EXM-065 tres herramientas obligatorias | OK | `toolchain/models.py:11-15`, `toolchain-policy.json:11-45` |
| RQ-EXM-066 matriz fijada y sin `latest` | PARCIAL | Loader rechaza `latest` (`policy.py:125-205`); dos combinaciones fijadas, sin checksums de plugin markers |
| RQ-EXM-067 preflight `READY` antes del intento | OK | Bloqueo implementado (`actions/examine.py:253-285`) y verificado con rutas reales (`READY_TO_START=True`) |
| RQ-EXM-068 instalación aislada y cero mutación | OK | `manager.py:203-225,339-365`; `tests/toolchain/test_manager.py:319` |
| RQ-EXM-069 health check real | OK | `manager.py:366-458`; `tests/toolchain/test_manager.py:228,284`; ejecución Gradle real con reportes válidos |
| RQ-EXM-070 fallo bloqueante | OK | `tests/exams/test_toolchain_integration.py:29-47` |
| RQ-EXM-071 `INCOMPLETE_INFRASTRUCTURE` sin nota | OK | `tests/exams/test_toolchain_integration.py:76-116`, `evaluation/models.py:363-381` |
| RQ-EXM-072 no mutación del proyecto | OK | Hash antes/después en `manager.py:185,222-238` |
| RQ-EXM-073 manifiesto reproducible | OK | `tests/exams/test_toolchain_integration.py:50-73`; `toolchain/models.py` |
| RQ-EXM-074 TeacherAgent no administra herramientas | OK | `tests/agents/test_teacher_agent.py`, `tests/exams/test_toolchain_integration.py` |
| RQ-EXM-075 seguridad de dependencias | PARCIAL | Repositorios declarados y repositories inyectados en buildscript aislado; faltan checksums de markers descargados |
| RQ-EXM-076 progreso visible de inicio | OK | `ExamPreparationList.show_preparing`, worker de preparación en `app.py`, avances en `ExamPreparationService` y `ExamineAction.start`; pruebas TUI y de integración |
| Integración en proyectos Android representativos | PARCIAL | Verificado sobre proyecto Gradle 9.5.0 / Kotlin 2.2.10 / AGP 9.3.3 con reportes reales; automatización con `FakeRunner` en `tests/toolchain/test_manager.py:414` |

## 4. Brechas críticas priorizadas

### P0 — impiden declarar la spec completa

1. **Contrato del evaluador no implementado.** La adenda exige
   `EvaluatorAgent.evaluate(request) -> EvaluationReport`
   (`requirements.md:649-674`, `design.md:600-625`). El código expone
   `build_report(...)` como proyector de un `ExamResult` ya calculado
   (`evaluation/exam_agent.py:57-74`); el cálculo sigue repartido entre
   `ExamineAction`, `ExamScorer` y `EvaluationEngine`.
2. **Subcriterios D1–D5 no evaluados de forma independiente.** T1/T2/T3, M1–M5 y
   A1–A7 existen como datos de rúbrica (`evaluation/rubric.py:206-382`) pero no
   hay analizadores que produzcan `CriterionResult` por subcriterio: el reporte
   replica la nota de la dimensión (`evaluation/exam_agent.py:254-278`). Esto
   invalida las reglas D2.2, D4.2 y D5.2 y las pruebas de aceptación 1, 6 y 10.
3. **PDF no determinista-exclusivo.** `ExamReportGenerator` sigue rendering
   `ExamResult` (`exams/report.py:58-59,122-137`) con secciones narrativas
   alimentadas por el LLM (`feedback`, `strengths`, `weaknesses`,
   `recommendations`: `:225-244`), tabla de cálculo propia y sección
   «Clean architecture» (`:229-232`). Las tablas R1–R12 se añaden como bloques
   adicionales (`:262-279`). No hay límite de 4 páginas.
4. **Checksums de toolchain pendientes.** La matriz cubre Gradle 8.4 y 9.5
   (`toolchain-policy.json:11-45`), injecta Detekt/KtLint en un workspace temporal
   (`manager.py:286-365`) y fue verificada contra un proyecto Android real con
   Gradle 9.5.0: los tres reportes estructurados se validaron y `READY_TO_START`
   quedó en `True`. Sigue pendiente fijar checksums de los markers de plugin
   descargados; proyectos con otras versiones reciben guía para ampliar la matriz.
5. **Especificación internamente contradictoria.** Los textos base de
   `spec.md`, `requirements.md`, `tasks.md` y los ADR siguen describiendo
   Markdown/PDF, `exam-default:v1`, Clean Architecture y `.md` para
   `/instructions`, aunque las adendas los reemplazan. La trazabilidad de
   `requirements.md:277-320` marca como pendientes o sin trazar requisitos que ya
   tienen pruebas.

### P1 — desviaciones funcionales o de diseño

6. ~~**Botones grandes en el inicio del examen.**~~ RESUELTO: la selección de
   `Iniciar examen` solo abre `ExamPreparationList` (`app.py:831-843`,
   `:1209-1221`); la barra compartida queda limitada a `/evaluate` y las pruebas
   verifican que no aparece en el flujo de examen
   (`tests/cli/tui/test_exam_confirmation.py:161-246`).
7. **Registro de verificadores y observaciones no mapeadas ausentes.** El diseño
   normativo (`design.md:825-827`) exige resolver cada método de verificación con
   un verificador y registrar `NOT_AVAILABLE` si falta; RQ-EXM-062 exige
   `unmapped_observations`. Ninguno existe en el código actual.
8. **Snapshot de definición no enlazado al intento.** Aunque la definición
   persistida contiene `definition_snapshot`/`definition_sha256`
   (`exams/definition.py:330-331`, `exams/store.py:125-137`), `ExamAttempt`
   declara esos campos sin poblarlos (`exams/models.py:215-216`,
   `exams/lifecycle.py:87-101`) y no hay prueba que verifique RQ-EXM-058 de extremo
   a extremo.
9. **Preparación no es estrictamente de solo lectura.** `ExamPreparationService`
   se documenta como validación sin estado (`exams/preparation.py:1,51-52`), pero
   ejecuta `ToolchainManager.prepare(...)`, que crea caché/workspace y corre
   tareas Gradle (`:66-85`, `toolchain/manager.py:197-207`). El árbol original se
   protege por hash, no por ausencia de ejecución.
10. **Toolchain no orquestado por EvaluatorAgent.** Las adendas exigen que
    `EvaluatorAgent` solicite y verifique la preparación
    (`requirements.md:903-913`); las llamadas reales están en
    `exams/preparation.py:66-85` y `actions/examine.py:202-213,253-264`.

### P2 — cobertura de pruebas insuficiente

11. Sin pruebas para: siete requisitos y pesos `0.20+0.20+0.20+0.10+0.10+0.15+0.05`
    del enunciado Domino real; `_detekt_not_configured`; manifest debug `info`;
    `_score_architecture` sin penalización por `info`; normalización objeto→lista
    sin consumir intento; conservación de `raw_score_50`/`suggested_grade` tras
    fallo total del LLM (`tasks.md:90-96`).
12. Sin pruebas de navegación Arriba/Abajo/Enter/Escape del panel, de
    `/instructions` (extensiones `.json`, rutas absolutas/relativas/`~`, cwd,
    ayuda bilingüe), ni de que abrir/cancelar el panel no crea estado
    (`tasks.md:101-115`).
13. Sin pruebas de widget de temporizador ni de aviso localizado al llegar a cero
    (`tasks.md:119-125`, RQ-EXM-039–042).
14. Sin pruebas de fórmulas D1–D5, límites 79.99%/80%/100%, deduplicación de
    severidades, falsos positivos MVVM, aplicabilidad Android, contenido de R1–R12,
    ausencia de prosa LLM, estabilidad numérica de `EvaluationReport`, ni
    integración EvaluatorAgent→TeacherAgent (`tasks.md:197-206`).
15. Sin integración real con proyectos Android representativos para validar la
    estrategia de inyección aislada (`tasks.md:246`).

## 5. Evidencia de ejecución

- `python -m pytest -q` → **674 passed in 27.07s**, 0 fallos.
- `ruff check . --fix` → **70 errores preexistentes** sin corrección automática
  segura; 6 correcciones solo con `--unsafe-fixes`. Los archivos Python
  modificados pasan `ruff check` enfocado.
- `CommandRouter.exam_preparation_status()` con proyecto
  `/Users/jorge/Downloads/Domino` e instrucciones
  `/Users/jorge/Downloads/domino-conquista.exam.json` → `READY_TO_START True`,
  `TOOLCHAIN_READY True`, sin blockers.
- Gradle 9.5.0 ejecutado en copia aislada: `lintDebug` `READY`, `detekt` y
  `ktlintCheck` `ISSUES_FOUND`; los tres con health check PASS y reportes
  estructurados válidos.
- Pruebas enfocadas de inicio/preparación → **21 passed**, incluidas la espera
  no bloqueante del panel y los avances localizados por etapa real.

## 6. Condiciones para declarar completa la spec 007

1. Unificar los documentos normativos en una sola versión vigente: eliminar o
   marcar como históricas las secciones Markdown/PDF, `exam-default:v1` y
   Clean Architecture; corregir RQ-EXM-002/014/018/035; actualizar ADR y `tasks.md`.
2. Implementar `EvaluatorAgent.evaluate(request)` y centralizar en él la
   evaluación de los analizadores y la producción de `EvaluationReport`.
3. Implementar evaluadores independientes para T1–T3, M1–M5 y A1–A7 con reglas
   versionadas, evidencia y `calculation_trace` verificable.
4. Generar el PDF únicamente desde `EvaluationReport`, sin secciones narrativas
   del LLM, sin «Clean Architecture», con catálogo localizado y límite de 4 páginas.
5. Registrar checksums de los plugin markers de `toolchain-policy.json:34-45` y
   automatizar el health check de integración con Gradle real en CI.
6. Implementar `unmapped_observations` y el registro de verificadores con
   `NOT_AVAILABLE`.
7. ~~Sustituir la barra Confirmar/Cancelar del inicio por el selector compacto y
   añadir las pruebas de TUI pendientes.~~ RESUELTO: ver filas RQ-EXM-033/036–038
   y el apartado 3.2.
8. Persistir y probar el snapshot/hash de la definición en el intento.
9. Ejecutar y documentar todas las pruebas de aceptación de `spec.md:892-916`
   y `spec.md:1099-1115`, además de la matriz de `requirements.md:805-828`.
10. Dejar `ruff check . --fix` sin errores o documentar las excepciones con su
    justificación y alcance.

## 7. Decisión pendiente recomendada

Antes de escribir más código, conviene aprobar una **revisión normativa única**
de `spec.md`, `requirements.md`, `design.md`, `tasks.md` y los ADR para que dejen
de convivir reglas incompatibles. Esta auditoría identifica las contradicciones;
su resolución debe hacerse mediante el flujo `SPEC → REQUIREMENT → DESIGN → TASK`
y registrarse en los ADR correspondientes, no interpretándolas silenciosamente
durante la implementación.

## 8. Cierre v2 de evaluación y reporte

- Rúbrica activa de examen: `unified-android:v2`; D4 divide 50% Clean
  Architecture (C1–C7) y 50% MVVM (M1–M6) con pesos declarados.
- Modelo por defecto alineado en configuración, docs y specs:
  `qwen2.5-coder:7b`, temperatura 0, tres intentos totales y metadata de
  prompt/modelo persistida en `llm_runs`.
- Corrección del error 404: el default temporal `qwen2.5-code:7b` no existe en
  Ollama; se restauró `qwen2.5-coder:7b` tras verificar `ollama list` y
  `POST /v1/chat/completions`.
- `ExamineAction` produce un único `EvaluationReport` y lo consumen `present()`,
  el PDF, el resumen Markdown, el historial y las explicaciones del teacher.
- El PDF usa ocho secciones v2, agrupa hallazgos, limita acciones a cinco,
  muestra evidencia `ruta:líneas`, cobertura/peso excluido y un máximo de
  cuatro páginas; no recalcula ninguna nota.
- Estados LLM no evaluables se excluyen del denominador, se declaran en la
  cobertura y nunca se convierten en cero; `LLM_UNAVAILABLE` marca el informe
  como `BLOCKED`.
- Corrección del error de esquema: los prompts declaran `claim`, `evidence_refs`,
  `kind`, `architecture` y los campos obligatorios de decisión; los esquemas
  rechazan alias y campos adicionales; las respuestas inválidas o incompletas
  siguen siendo `NOT_EVALUATED`, nunca `PASS` (RQ-EVA-048, RQ-EXM-085).
- Un objeto de decisión solitario se envuelve en su array batch antes de
  validar; los prompts declaran los wrappers `criteria`, `clean_architecture` y
  `mvvm`.
- Evidencia verificada: `python -m pytest -q` → **700 passed**.
- Smoke en vivo: `/ask` responde con `qwen2.5-coder:7b`; `/evaluate` ya no
  produce HTTP 404 y llega al LLM con el payload estructurado.
- `supersedes_report_id` se preserva desde los metadatos administrativos del
  intento hasta el reporte; el comando completo de reevaluación sigue pendiente.
- Pendiente: fixture de regresión automatizada con el PDF de Domino Conquista.
- Pendiente y sin inventar: checksums reales de los markers Gradle de
  `toolchain-policy.json`; requiere descarga/artefactos verificables.
