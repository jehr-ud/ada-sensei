# Refactorización 007 Examine

Este paquete actualiza el flujo de preparación e inicio de exámenes y añade la
especificación del temporizador visible en el TUI.

Archivos:
- `IMPLEMENTATION-STATUS.md`: auditoría de completitud frente al código y las
  pruebas; estado real de cada requisito, contradicciones normativas y brechas.
- `spec.md`: comportamiento y criterios de aceptación.
- `requirements.md`: requisitos trazables RQ-EXM-032 a RQ-EXM-076 y preservación
  de los requisitos previos.
- `design.md`: arquitectura propuesta, flujo, UI y timer.
- `tasks.md`: lista de implementación y pruebas.
- `ADR-026-exam-preparation-and-timer.md`: decisión arquitectónica propuesta.
- `PROMPT-OpenCode.md`: instrucciones de implementación.

El paquete se debe integrar con el repositorio actual después de revisar
`AGENTS.md` y los componentes existentes. No sobrescribe automáticamente los
archivos del proyecto.


## Adenda 2026-11-20

Se incorpora la especificación normativa del informe determinista integral, la rúbrica unificada y la separación de responsabilidades entre EvaluatorAgent (evalúa) y TeacherAgent (consume y enseña). La adenda dentro de spec.md, requirements.md y design.md prevalece sobre reglas anteriores contradictorias.


## Definición de exámenes

En esta versión, el docente debe proporcionar una definición JSON estructurada. Consulta `exam-definition.schema.json` y `examples/domino-conquista.exam.json`. La extracción automática desde Markdown/PDF queda explícitamente fuera de alcance. El JSON validado es la fuente única de requisitos para `EvaluatorAgent`.


## Preparación automática de herramientas estáticas (2026-11-21)

Se incorpora `ToolchainManager` bajo orquestación de `EvaluatorAgent`. Android
Lint (AGP), Detekt y KtLint deben quedar preparados y superar health checks
reales antes de iniciar. La preparación usa versiones fijadas y workspace/caché
aislados; no modifica el proyecto original ni instala herramientas globalmente.
Si falla, el preflight bloquea el examen; un fallo posterior marca la evaluación
como incompleta por infraestructura, nunca como cero del estudiante. Consulta
`toolchain-policy.json` y `ADR-028-toolchain-preparation.md`. El inicio muestra
`Preparando…` y avances reales por etapa mientras se prepara el toolchain, sin
congelar el TUI (RQ-EXM-076).
