# Requisitos — 007 Examine: preparación, inicio y temporizador

## RQ-EXM-001 — Identidad del examen
Se conservan separados `student_id`, `project_id`, `exam_id`, `attempt_id` y
`exam_attempt_id`.

## RQ-EXM-002 — Definición autoritativa
El examen se carga desde un archivo de instrucciones del docente. En esta
iteración, el formato admitido por el flujo `/instructions` es Markdown (`.md`).
`ExamDefinitionLoader` es el único responsable de interpretar y normalizar el
enunciado; debe preservar el texto original y la ruta fuente.

## RQ-EXM-003 — Inicio transaccional
El sistema solo crea y persiste `ExamAttempt`, definición, eventos de inicio y
documentación después de que el estudiante elija explícitamente `Empezar examen`
y todas las precondiciones hayan pasado. La operación debe crear exactamente
un intento.

## RQ-EXM-004 — Finalización
El sistema conserva el flujo de finalización y la inmutabilidad del intento
completado.

## RQ-EXM-005 — Conteo de consultas
El sistema cuenta `/ask` exitosos mediante eventos `ASK_COMPLETED`; no usa
texto de terminal ni salida del LLM.

## RQ-EXM-006 — Historial de eventos
El sistema persiste eventos de examen con id, attempt id, tipo, timestamp,
question id, duración y metadata.

## RQ-EXM-007 — Duración autoritativa
El sistema calcula duración desde timestamps persistidos. El reloj de pantalla
es solo presentación y nunca constituye evidencia ni fuente de verdad.

## RQ-EXM-008 — Documentación del estudiante
Se conservan `DocumentationRules`, globs, archivos requeridos y modo advisory
del examen existente.

## RQ-EXM-009 — Documentación generada
Al iniciar se crea `docs/ada-sensei/exams/<exam-slug>/` con los archivos
definidos por la especificación existente, sin sobrescribir archivos del
estudiante que no tengan el marcador generado por ADA Sensei.

## RQ-EXM-010 — Evidencia del proyecto
Se reutiliza el pipeline de `006-evaluate` para inspección, build, pruebas
unitarias, Android Lint y Detekt.

## RQ-EXM-011 — Sin pruebas instrumentadas
No se ejecuta `connectedAndroidTest`; `--instrumented` continúa rechazado.

## RQ-EXM-012 — Requisitos funcionales
Se conservan ids estables, pesos funcionales válidos y matching específico del
examen.

## RQ-EXM-013 — Calidad de código
Se conserva la evaluación determinista y la interpretación LLM acotada.

## RQ-EXM-014 — Arquitectura limpia
La puntuación se basa únicamente en señales observadas del proyecto.

## RQ-EXM-015 — Pruebas
Las pruebas unitarias no disponibles se reportan como no evaluadas, nunca como
éxito supuesto.

## RQ-EXM-016 — Prácticas Android
Se conservan las reglas deterministas basadas en Android Lint.

## RQ-EXM-017 — Rúbrica de proceso
Duración y uso de `/ask` se evalúan solo si el enunciado establece límites,
usando las bandas de la rúbrica versionada.

## RQ-EXM-018 — Pesos de examen
Se conserva `exam-default:v1` y sus pesos actuales.

## RQ-EXM-019 — Puntaje determinista
El puntaje se calcula a partir de dimensiones evaluadas; denominador cero
produce `not evaluated`.

## RQ-EXM-020 — Rango del puntaje
El puntaje bruto se mantiene en el rango 0–50.

## RQ-EXM-021 — Nota sugerida
La nota sugerida se deriva determinísticamente del puntaje bruto.

## RQ-EXM-022 — Suficiencia de evidencia
La ausencia de evidencia nunca se interpreta como cumplimiento.

## RQ-EXM-023 — Informe de arquitectura
Se conserva la explicación de arquitectura fundamentada en evidencias.

## RQ-EXM-024 — Informe PDF
Se conserva el informe PDF detallado. El PDF se escribe dentro del proyecto
examinado, en el subárbol propio `docs/ada-sensei/exams/<exam-slug>/report.pdf`,
junto a la documentación generada del examen. No se escribe en el directorio de
datos de ADA Sensei.

## RQ-EXM-025 — Salida estructurada
Las respuestas estructuradas del LLM siguen usando el pipeline compartido y
sus límites de intentos.

## RQ-EXM-026 — Persistencia
Se conserva la persistencia del resultado y se reportan fallos como limitaciones.

## RQ-EXM-027 — Historial
El resultado final se agrega al historial del estudiante.

## RQ-EXM-028 — Integridad del proyecto
La evaluación no modifica archivos fuente del estudiante.

## RQ-EXM-029 — Nota sugerida identificada
El informe identifica la nota como sugerida y generada por ADA Sensei.

## RQ-EXM-030 — Afirmaciones sustentadas
Se distinguen evidencias observadas, documentadas e inferidas.

## RQ-EXM-031 — Integridad de métricas
Duración y consultas se derivan del estado/eventos persistidos.

## RQ-EXM-032 — Preflight obligatorio
Antes de iniciar, `ProjectPreflight` debe comprobar que la ruta configurada
existe y es directorio, que se detecta proyecto Android y que Gradle/JDK 17+/
Android SDK están disponibles. No ejecuta Gradle ni modifica el proyecto.

## RQ-EXM-033 — Panel de preparación
Al seleccionar `Iniciar examen`, el TUI presenta un panel de preparación
compacto, con instrucciones y estado de proyecto/instrucciones. No muestra
botones grandes Confirmar/Cancelar. Usa una lista de opciones con cursor y
navegación Arriba/Abajo/Enter/Escape, siguiendo el patrón `LanguageList`.

## RQ-EXM-034 — Configuración de proyecto
`/project <ruta>` configura y persiste en el contexto existente la ruta raíz
del proyecto. Acepta rutas absolutas y relativas, normaliza `~`, resuelve las
relativas desde el cwd del proceso y no cambia el cwd.

## RQ-EXM-035 — Configuración de instrucciones
`/instructions <ruta>` configura el archivo Markdown del docente. Debe ser un
archivo regular, legible y no vacío. La definición se valida con
`ExamDefinitionLoader`. No inicia el examen ni copia/modifica el archivo.

## RQ-EXM-036 — Requisitos obligatorios
No se puede iniciar si falta estudiante, proyecto válido, preflight correcto,
archivo Markdown válido o si ya existe un intento activo. Se muestran todos
los bloqueos conocidos y se permite corregir las rutas sin cerrar el panel.

## RQ-EXM-037 — Revalidación al iniciar
Al elegir `Empezar examen`, se vuelven a ejecutar las validaciones. La
validación no crea estado. Si falla, no se crea intento, timer, evento ni docs.

## RQ-EXM-038 — Opción explícita
El inicio requiere seleccionar `Empezar examen`. Abrir el panel de preparación
no inicia nada. `Volver`/Escape cancela la preparación sin efectos secundarios.
No existe un segundo diálogo de botones Confirmar/Cancelar.

## RQ-EXM-039 — Temporizador TUI
Durante un examen activo se muestra tiempo transcurrido `HH:MM:SS`. Si hay
`allowed_duration_seconds`, se muestra además tiempo restante y vencimiento.
Si no hay límite, no se inventa un countdown.

## RQ-EXM-040 — Temporizador no bloqueante
La actualización visual es periódica y no bloquea el TUI. Al reanudar, el
tiempo se reconstruye desde `started_at`. Los ticks no se persisten ni puntúan.

## RQ-EXM-041 — Estado de consultas
Durante el examen se muestra el número de `/ask` exitosos y, si está definido,
el límite. El dato procede del event log.

## RQ-EXM-042 — Límite alcanzado
Al agotarse el tiempo se muestra aviso localizado. El examen no se finaliza
automáticamente en esta iteración; el estudiante usa `Finalizar examen`.

## RQ-EXM-043 — Configuración inmutable del intento
Cambiar `/project` durante un examen activo no altera el proyecto asociado al
intento actual; solo afecta un examen posterior.

## RQ-EXM-044 — CLI no interactivo
Los comandos directos `exam-init`/`--yes` también deben ejecutar las mismas
precondiciones y `ProjectPreflight`. Ninguna opción no interactiva puede
saltarse la validación.

## RQ-EXM-045 — Localización
Todas las cadenas nuevas existen en `es-CO` y `en-US`, con fallback
determinista. El panel usa el locale actual y el intento conserva el snapshot
del idioma al iniciar.

## RQ-EXM-046 — Compatibilidad
Se mantienen las reglas de rúbrica, scoring, evidence pipeline, PDF, persistencia,
eventos, idioma y finalización del examen ya existentes.

## RQ-EXM-047 — Finalización compacta
Si se presenta una confirmación TUI para finalizar, utiliza el selector compacto
de opciones y no botones grandes, manteniendo confirmación explícita.

## RQ-EXM-048 — Progreso de finalización
Durante la finalización, el TUI emite mensajes localizados de avance por etapa:
inspección del proyecto, build, pruebas unitarias, Android Lint, Detekt,
interpretación del modelo e informe. Los mensajes se derivan de las etapas
reales del pipeline, nunca de un temporizador simulado, y no alteran el
resultado ni la puntuación.

## RQ-EXM-049 — Apertura del informe
Tras generar el PDF, el TUI lo abre con el visor del sistema de forma
best-effort: si no hay visor disponible, no falla ni cambia el resultado. La
apertura se controla con un ajuste de configuración `tools.open_report`
(por defecto activado). El CLI no interactivo no abre el PDF.

## RQ-EXM-050 — Ruta del informe en la salida
El resultado de finalización expone la ruta del PDF dentro del proyecto para
que el TUI la muestre y pueda abrirla.

## Matriz de trazabilidad

| Requisito | Componente principal | Prueba requerida |
|---|---|---|
| RQ-EXM-032, 036, 037, 044 | `ProjectPreflight`, `ExamPreparationService` | rutas ausentes, proyecto inválido, herramientas ausentes, preflight CLI |
| RQ-EXM-033, 038 | `ExamPreparationScreen` / `LanguageList` pattern | composición, teclado, cancelación, sin side effects |
| RQ-EXM-034 | parser/handler `/project` | rutas absoluta/relativa, `~`, cwd sin cambios |
| RQ-EXM-035 | parser/handler `/instructions`, `ExamDefinitionLoader` | `.md`, vacío, ilegible, definición inválida |
| RQ-EXM-039, 040, 042 | `ExamStatusBar` / `ExamTimer` | elapsed, remaining, no limit, non-blocking, resume, timeout |
| RQ-EXM-041 | `ExamEventBridge` / status presenter | ask count desde eventos |
| RQ-EXM-043 | `ExamAttempt` snapshot | cambiar ruta no altera intento |
| RQ-EXM-045 | locale UI strings | tests es-CO/en-US y fallback |
| RQ-EXM-046, 047 | `ExamineAction`, finish TUI | regresión motor y selector compacto |
| RQ-EXM-024, 050 | `ExamReportGenerator`, `ExamDocs` | PDF dentro de `docs/ada-sensei/exams/<slug>/`, ruta expuesta |
| RQ-EXM-048 | `EvidenceCollector`, `ExamineAction`, TUI | mensajes por etapa, sin efecto en el resultado |
| RQ-EXM-049 | `tools.opener`, config `tools.open_report` | apertura best-effort, toggle, sin fallo |
