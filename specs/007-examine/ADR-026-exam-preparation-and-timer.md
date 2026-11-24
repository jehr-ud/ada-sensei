# ADR-026 — Preparación explícita del examen y temporizador de presentación

## Estado
Aceptado (panel de inicio implementado; temporizador pendiente)

## Contexto

El flujo anterior presenta controles grandes Confirmar/Cancelar al seleccionar
`Iniciar examen`, reduciendo el espacio visible para el enunciado y ofreciendo
una interacción inconsistente con el selector compacto de idioma. Además, el
estudiante necesita configurar explícitamente el proyecto Android y el archivo
de instrucciones antes de iniciar.

## Decisión

Adoptar un panel de preparación con lista compacta y navegación por teclado.
La validación pesada del toolchain se ejecuta en un worker: el panel muestra
`Preparando…` y el log emite avances localizados por etapa real antes de crear
el intento, para que la espera no parezca un bloqueo (RQ-EXM-076).
inspirado en `LanguageList`. La configuración se realiza mediante
`/project <ruta>` y `/instructions <ruta>`. `Empezar examen` es la única acción
que inicia el intento después de validar ambas rutas, identidad y preflight.

El temporizador se presenta en el TUI a partir de `ExamAttempt.started_at`.
El dominio y el event log continúan siendo la fuente de verdad para duración y
métricas. No se persisten ticks.

## Consecuencias

- Inicio guiado y consistente con el resto del TUI.
- Ningún intento o timer se crea antes de una acción explícita y válida.
- Se requiere persistir la ruta de instrucciones en el contexto apropiado.
- La UI debe refrescar el tiempo sin bloquear la interacción.
- El motor de scoring, los modelos de resultado y el PDF permanecen intactos.
