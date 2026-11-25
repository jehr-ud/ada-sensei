# ADR-030 — Resolución independiente de recursos de examen

## Estado
Aceptado (2026-11-25). Prevalece sobre ADR-026 y sobre cualquier texto base que
identifique `/instructions` con la definición JSON del examen.

## Contexto

`CommandRouter._examine_start()` reutilizaba `ExamineStartCommand.statement`
como `SessionContext.instructions_path`, y `/instructions` validaba ese valor con
`ExamDefinitionLoader`. Por tanto, un archivo como
`domino-conquista.exam.json` podía persistirse como instrucciones. El mensaje
`instructions file is not readable: ...` ocultaba una confusión de recursos, no
un problema de permisos. Además, las rutas relativas dependían del directorio de
trabajo del proceso y las sesiones persistían rutas absolutas sin validarlas al
cargarlas.

## Decisión

1. Separar los recursos en campos independientes:
   `instructions_path`, `exam_definition_path`, `project_path`.
2. `/instructions <path>` acepta únicamente instrucciones Markdown (`.md`).
   `/exam-definition <path>` y `exam-init <path>.json` configuran la definición
   JSON validada. Ningún cargador reinterpreta un recurso del otro tipo.
3. Centralizar la resolución en `ada_sensei.resources.paths.ResourceResolver`,
   basada en `pathlib.Path`: `~` se expande, las relativas se resuelven contra
   un directorio base explícito y documentado, y los recursos internos se leen
   con `importlib.resources`.
4. Persistir referencias relativas al directorio base cuando sea posible. Las
   referencias absolutas externas se validan en tiempo de carga; si no existen
   en el sistema actual se informa el recurso y la ruta resuelta, sin
   sustituirlas por otra ruta.
5. Los errores de configuración identifican `Resource`, `Resolved path` y
   `Reason`.

## Consecuencias

- `/instructions` deja de aceptar la definición JSON; las sesiones heredadas
  con una definición JSON en `instructions_path` se migran explícitamente a
  `exam_definition_path` solo si la definición sigue siendo válida.
- El panel de preparación muestra y valida ambos recursos.
- El empaquetado incluye los recursos internos (instrucciones, schema,
  configuración de learning path y política de toolchain).
- No se modifica la lógica de evaluación, las notas ni el contrato de
  `EvaluationReport`.
