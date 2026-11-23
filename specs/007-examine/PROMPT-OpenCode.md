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


## Nueva prioridad: evaluación integral determinista

La adenda normativa de `spec.md`, `requirements.md` y `design.md` prevalece
sobre cualquier regla antigua de rúbrica o arquitectura.

1. `EvaluatorAgent` debe ser el único evaluador. `TeacherAgent` solo consume
   `EvaluationReport` y lo usa para tutoría; nunca calcula notas.
2. Sustituye la rúbrica anterior por 40% funcionalidad, 20% pruebas, 15%
   calidad, 15% MVVM y 10% buenas prácticas Android.
3. Implementa exactamente las reglas de cada tabla D1–D5 y R1–R12 de la adenda.
4. Calidad: Detekt 40%, Android Lint 35%, KtLint 25%.
5. MVVM reemplaza Clean Architecture. Buenas prácticas Android contiene siete
   subcriterios con los pesos especificados.
6. El umbral de pruebas es 80% de requisitos funcionales con pruebas asociadas;
   muestra cobertura de requisitos separada de cobertura de líneas.
7. El PDF se genera desde el modelo tipado `EvaluationReport`, sin LLM, con
   tablas, IDs, estados, evidencias y fórmulas reproducibles. Máximo 4 páginas.
8. No rellenes vacíos con suposiciones. Los errores de herramientas se reportan
   como estados de infraestructura y no como fallos del estudiante.
9. TeacherAgent puede explicar hallazgos en diálogo, citando sus IDs, pero no
   altera resultados ni contenido oficial del PDF.
10. Inspecciona `AGENTS.md`, specs y código existente antes de implementar.
    Reutiliza componentes; no crees motores duplicados.
11. Antes de implementar, presenta un mapa de componentes existentes y un plan
    de migración desde la rúbrica previa, incluyendo persistencia/versionado.
12. Ejecuta pruebas y reporta solo resultados realmente obtenidos.


## Cambio normativo: definición JSON del examen

Implementa la adenda JSON obligatoria de `spec.md`, `requirements.md` y `design.md`. No mantengas Markdown/PDF como fuentes autoritativas de requisitos. Reutiliza el código existente y evita duplicar motores. Valida `exam-definition.schema.json`, conserva snapshot/hash, presenta errores al docente mediante TeacherAgent y entrega a EvaluatorAgent solo `ExamDefinition` validado. TeacherAgent no puntúa. EvaluatorAgent es el único responsable de evaluar y generar `EvaluationReport`. Implementa pruebas para cada RQ-EXM-052 a RQ-EXM-063. El requisito legado 052 se identifica `RQ-EXM-052-DEBUG`; las rúbricas previas migran a `unified-android:v1` sin alias.


## Cambio normativo: preparación automática del toolchain estático

Implementa la adenda `Preparación y gestión automática del toolchain estático`
en `spec.md`, `requirements.md`, `design.md`, ADR-028 y `toolchain-policy.json`.

1. `EvaluatorAgent` es el único que solicita y verifica la preparación; reutiliza
   o crea `ToolchainManager` determinista. `TeacherAgent` solo comunica estados.
2. Android Lint, Detekt y KtLint son obligatorios para completar D3. Android Lint
   se ejecuta desde AGP; Detekt y KtLint se resuelven con versiones fijadas.
3. No usar `latest`, no instalar globalmente y no modificar permanentemente el
   proyecto del estudiante. No ejecutar auto-correct/format.
4. Preparar el toolchain durante preflight, antes de crear `ExamAttempt` y timer.
5. Exigir health check real y reporte estructurado; presencia de plugin/tarea no
   equivale a ejecución correcta.
6. Si no puede prepararse una herramienta, bloquear inicio sin intento/timer. Si
   falla tras iniciar, estado `INCOMPLETE_INFRASTRUCTURE`, sin nota final completa
   ni penalización al estudiante.
7. Mantener matriz de compatibilidad verificada AGP/Kotlin/Gradle/Detekt/KtLint.
   No asumir que una inyección por init script funciona en todos los builds;
   demostrarlo con proyectos de integración.
8. Persistir versiones, checksums, comandos, variantes, hashes y resultados en
   `ToolchainManifest`/`ToolExecutionEvidence`.
9. Implementar y probar RQ-EXM-064 a RQ-EXM-075. Actualiza tasks y traceability.
