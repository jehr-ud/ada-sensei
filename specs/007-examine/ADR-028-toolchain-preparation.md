# ADR-028 — Preparación aislada y reproducible de herramientas estáticas

- Estado: Propuesta normativa
- Fecha: 2026-11-21

## Contexto
La rúbrica requiere Android Lint, Detekt y KtLint. Detectar que una herramienta
no existe y continuar genera una evaluación incompleta; instalar plugins
directamente en el proyecto del estudiante puede modificar sus archivos y
romper su build.

## Decisión
`EvaluatorAgent` orquesta un `ToolchainManager` determinista. Este detecta
compatibilidad, resuelve versiones fijadas, prepara dependencias en caché
ADA Sensei/workspace temporal y ejecuta health checks reales. Android Lint se
obtiene de AGP; Detekt y KtLint se resuelven con versiones de una matriz
verificada. No se usan versiones flotantes ni instalaciones globales.

El preflight prepara el toolchain antes de crear el intento y arrancar el timer.
Si no puede dejar las tres herramientas listas, bloquea el inicio. Si ocurre un
fallo de infraestructura después del inicio, el reporte queda incompleto, sin
nota final completa y sin penalización al estudiante. El código original nunca
se modifica; no se ejecutan tareas de auto-fix.

`TeacherAgent` solo comunica el estado. No administra herramientas ni evalúa.

## Consecuencias
- Evaluaciones reproducibles con manifiesto de versiones y hashes.
- Preflight puede tardar más por resolución/descarga inicial.
- Se requiere mantener una matriz de compatibilidad verificada para AGP, Kotlin,
  Gradle, Detekt y KtLint.
- Proyectos incompatibles o sin acceso a dependencias pueden quedar bloqueados
  hasta resolver infraestructura.
- La configuración temporal debe probarse por tipo de proyecto Android y no
  puede asumirse que un Gradle init script sirve para todos los builds.
