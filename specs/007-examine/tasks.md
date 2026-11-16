# Tareas — refactorización de 007 Examine

## 0. Inspección obligatoria

- [ ] Leer `AGENTS.md` y todos los artefactos actuales de `007-examine`,
  `002-cli`, `001-foundation`, `006-evaluate`, `0010-language-selection` y
  `009-agent-orchestration`.
- [ ] Inspeccionar el flujo real de `exam-init` en TUI, parser, router,
  `ExamineAction`, `ProjectPreflight`, `SessionContext` y configuración.
- [ ] Inspeccionar `LanguageList` y su montaje real en la bienvenida y en
  Change language; reutilizar ese patrón de widget/teclado.
- [ ] Identificar el origen de los botones grandes Confirmar/Cancelar y
  eliminar el flujo duplicado, sin mantener dos confirmaciones.
- [ ] Verificar qué campos canónicos ya existen para project path e
  instrucciones; evitar duplicar configuración.

## 1. Comandos y contexto

- [ ] Añadir `/project <ruta>` al registry/parser compartido.
- [ ] Resolver rutas absolutas, relativas y `~` con cwd del proceso.
- [ ] Guardar la ruta en el campo canónico existente.
- [ ] Añadir `/instructions <ruta>` al registry/parser compartido.
- [ ] Validar extensión `.md`, archivo regular, legible y no vacío.
- [ ] Guardar ruta en contexto/configuración existente con persistencia
  compatible.
- [ ] Añadir ayuda bilingüe a `/help` y descripciones del selector.
- [ ] Añadir pruebas para ambos comandos y para que cwd no cambie.

## 2. Servicio de preparación

- [ ] Implementar o extender `ExamPreparationService` como capa de aplicación.
- [ ] Integrar identidad, proyecto, `ProjectPreflight`, instrucciones y
  `ExamDefinitionLoader`.
- [ ] Devolver todos los bloqueos de validación en una estructura tipada.
- [ ] Garantizar que validación no crea intento, eventos, timer ni docs.
- [ ] Volver a validar al iniciar.
- [ ] Hacer validación final y creación de intento en una operación protegida
  contra doble dispatch.
- [ ] Aplicar preflight también a CLI y `--yes`.

## 3. Panel de preparación TUI

- [ ] Crear/extender pantalla/panel de preparación de examen.
- [ ] Reutilizar patrón `LanguageList` (lista compacta, cursor `>`, teclado).
- [ ] Eliminar botones grandes Confirmar/Cancelar de la preparación.
- [ ] Mostrar explicación y comandos `/project` y `/instructions`.
- [ ] Mostrar estado de estudiante, proyecto, preflight e instrucciones.
- [ ] Añadir opciones `Empezar examen` y `Volver`.
- [ ] Deshabilitar o bloquear con mensaje localizado `Empezar examen` si hay
  precondiciones incumplidas.
- [ ] Mantener visible el contenido previo y el área de conversación.
- [ ] Implementar Arriba/Abajo/Enter/Escape y restauración correcta del foco.
- [ ] Permitir que el estudiante escriba comandos de configuración y volver a
  actualizar el estado del panel.
- [ ] Probar terminal estrecha/pequeña y wrap de texto.
- [ ] Confirmar que abrir/cancelar el panel no crea side effects.

## 4. Inicio de examen

- [ ] Cargar Markdown con `ExamDefinitionLoader` sin reimplementar parsing.
- [ ] Preservar original statement y source path.
- [ ] Revalidar todo al elegir `Empezar examen`.
- [ ] Crear exactamente un `ExamAttempt` al pasar todas las validaciones.
- [ ] Conservar snapshot de proyecto, locale, definición, límites y rúbrica.
- [ ] Crear documentación generada solo después de iniciar.
- [ ] Bloquear doble Enter/doble click.
- [ ] Mantener compatible la interfaz CLI directa.

## 5. Temporizador y estado activo

- [ ] Añadir indicador compacto persistente de examen activo.
- [ ] Mostrar elapsed `HH:MM:SS`.
- [ ] Mostrar remaining si `allowed_duration_seconds` está definido.
- [ ] Mostrar aviso localizado al alcanzar cero sin auto-finalizar.
- [ ] Mostrar contador `/ask` y límite si existe.
- [ ] Refrescar mediante scheduler no bloqueante del TUI.
- [ ] Reconstruir reloj al reanudar desde `started_at`.
- [ ] Detener refresco al finalizar/cancelar la sesión TUI.
- [ ] No persistir ticks ni usarlos en scoring.

## 6. Finalización y regresión

- [ ] Si se presenta confirmación de finalización, usar lista compacta
  `Finalizar examen` / `Continuar`.
- [ ] Conservar semántica de `exam-finish`, ask bridge, evidencia, score y PDF.
- [ ] Verificar que cambio de `/project` durante examen no modifica el intento.
- [ ] Ejecutar pruebas de 007-examine, 006-evaluate, CLI/TUI, locale y storage.
- [ ] Añadir pruebas de integración desde configuración hasta PDF final.
- [ ] Actualizar traceability y documentación/help.
- [ ] Registrar ADR si el diseño real requiere decisión arquitectónica nueva.

## Definición de terminado

- [ ] Los requisitos nuevos tienen pruebas automatizadas o una justificación
  documentada.
- [ ] No hay botones grandes Confirmar/Cancelar en el inicio de examen.
- [ ] El examen no puede comenzar sin proyecto Android válido e instrucciones
  Markdown válidas.
- [ ] El temporizador se muestra y es reconstruible desde el timestamp
  persistido.
- [ ] No se ha duplicado parser, preflight, loader, lifecycle, scoring o
  persistencia.
- [ ] No se han modificado las reglas existentes de evaluación.
