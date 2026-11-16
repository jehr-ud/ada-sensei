# Prompt para OpenCode — Refactorizar inicio y sesión de examen ADA Sensei

Implementa la refactorización descrita en `specs/007-examine/` (spec,
requirements, design, tasks y ADR-026).

## Reglas obligatorias

1. Lee `AGENTS.md` y los specs relacionados antes de editar.
2. Inspecciona el código real. Los nombres de clases del diseño son sugerencias:
   reutiliza componentes equivalentes existentes y evita duplicados.
3. Sigue `SPEC → REQUIREMENT → DESIGN → TASK → IMPLEMENTATION → TEST → EVIDENCE`.
4. No te limites a actualizar documentación: implementa el flujo completo.
5. No cambies el motor de evaluación, rúbrica, puntuación, evidencias, PDF,
   persistencia del resultado ni la semántica de `ExamDefinition`.
6. No uses botones grandes Confirmar/Cancelar para iniciar. Reutiliza el patrón
   de lista compacta de `LanguageList` con cursor `>`, Arriba/Abajo/Enter/Escape.
7. `/project <ruta>` y `/instructions <ruta>` deben funcionar desde el TUI y
   por el router/CLI compartido cuando corresponda.
8. No permitas iniciar sin proyecto Android válido, preflight correcto,
   estudiante e instrucciones `.md` válidas.
9. Revalida inmediatamente antes de crear el intento. La validación no debe
   crear intento, timer, eventos ni documentos.
10. Aplica `ProjectPreflight` también a la ruta no interactiva `--yes`.
11. El timer visual se deriva de `started_at`, no es evidencia, no se persisten
    ticks y no debe bloquear el TUI.
12. Mantén bilingüismo `es-CO`/`en-US`.
13. No modifiques archivos fuente del estudiante.
14. Evita cambios destructivos de datos/configuración; preserva compatibilidad
    con sesiones y registros anteriores.
15. No introduzcas auto-finalización al agotarse el tiempo.

## Pasos de implementación

- Primero informa brevemente qué componentes actuales encontraste y qué
  reutilizarás.
- Actualiza tareas a medida que se completen.
- Implementa comandos, contexto, servicio de preparación, panel TUI, inicio
  transaccional y timer.
- Añade pruebas unitarias, TUI e integración con reloj inyectable.
- Ejecuta el conjunto de pruebas relevante y reporta resultados reales.
- Revisa `git diff` para confirmar que no hay cambios no relacionados.
- Actualiza traceability y ADR si la implementación difiere del diseño.

## Criterios de aceptación manual

Desde cualquier directorio:
1. iniciar `ada-sensei`;
2. seleccionar `Iniciar examen`;
3. ver instrucciones y estados, sin botones grandes;
4. ejecutar `/project /ruta/al/proyecto-android`;
5. ejecutar `/instructions /ruta/al/examen.md`;
6. volver al panel y comprobar estados;
7. seleccionar `Empezar examen`;
8. ver el estado activo, tiempo transcurrido/restante y contador `/ask`;
9. finalizar y verificar resultado/PDF sin regresiones.

Al final entrega un resumen de archivos modificados, pruebas ejecutadas,
resultados, limitaciones y cualquier decisión pendiente. No afirmes que algo
está probado si no ejecutaste la prueba.
