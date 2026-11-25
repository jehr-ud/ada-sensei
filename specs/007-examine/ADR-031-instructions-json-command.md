# ADR-031 — `/instructions` como comando único de definición JSON

## Estado
Aceptado (2026-11-25). Reemplaza la decisión de interfaz de ADR-030 y cualquier
texto que exija `/exam-definition` como comando visible.

## Contexto
La separación introducida por ADR-030 hizo que `/instructions` aceptara solo
Markdown y que la definición JSON se configurara con `/exam-definition`. El flujo
real de preparación necesita la definición JSON validada, y el usuario indicó
que el comando histórico `/instructions <ruta.json>` debe seguir siendo la forma
de configurarla. El problema original de lectura era de resolución de rutas, no
de identidad del comando.

## Decisión
1. `/instructions <ruta>` es el único comando visible para configurar o mostrar
   la definición JSON del examen. Debe existir, ser un archivo regular legible y
   validarse con `exam-definition.schema.json` y las validaciones semánticas.
2. `/exam-definition` se elimina del parser, del router, de la ayuda y del TUI.
3. Internamente la definición puede permanecer en `exam_definition_path` para no
   mezclarla con otros identificadores. `instructions_path` queda como campo
   heredado de sesión y se muestra como la misma ruta de definición en el panel.
4. Se conservan `ResourceResolver`, `ResourceReference`, `importlib.resources`,
   la migración de sesiones heredadas y los errores con recurso/ruta/razón de
   ADR-030.
5. El Markdown de instrucciones no es una fuente autoritativa ni se valida en el
   preflight del examen.

## Consecuencias
- Los docentes vuelven a usar `/instructions ~/Downloads/domino-conquista.exam.json`.
- No hay dos comandos competidores para la misma definición.
- Las rutas relativas, `~`, permisos, Unicode y referencias entre sistemas siguen
  resolviéndose de forma centralizada y sin fallback silencioso.
