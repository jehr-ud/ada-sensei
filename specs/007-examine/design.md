# Diseño — 007 Examine: preparación y temporizador TUI

## Principios

1. Reutilizar la infraestructura existente: `ExamineAction`, `ExamDefinitionLoader`,
   `ProjectPreflight`, `ExamLifecycle`, `ExamStore`, `ExamEventBridge`,
   `LocaleService`, `ActionRegistry` y el router.
2. La interfaz presenta estado; no implementa reglas de dominio ni scoring.
3. Validar dos veces: al mostrar el estado de preparación y justo antes de iniciar.
4. Ninguna validación crea un intento ni modifica el proyecto.
5. La selección de idioma es la referencia de interacción visual/teclado; no
   duplicar su catálogo ni su lógica de locale.

## Componentes propuestos

Los nombres son propuestas de diseño. Antes de crearlos, inspeccionar los
componentes equivalentes existentes y extenderlos en lugar de duplicarlos.

### `ExamPreparationService` (application/action layer)

Responsabilidades:

- leer las rutas configuradas del `SessionContext`/configuración existente;
- validar archivo de instrucciones mediante `ExamDefinitionLoader`;
- ejecutar `ProjectPreflight` para el proyecto configurado;
- comprobar identidad y ausencia de examen activo;
- devolver un resultado inmutable de validación sin crear estado.

Modelo sugerido:

```python
class ExamPreparationStatus(BaseModel):
    student_ready: bool
    project_path: str | None
    project_ready: bool
    project_blockers: list[str]
    instructions_path: str | None
    instructions_ready: bool
    instruction_blockers: list[str]
    active_exam: bool
    ready_to_start: bool
```

No almacenar un `ExamDefinition` mutable como fuente de verdad entre el
preflight y el inicio. Al confirmar, volver a cargar la definición y validar
otra vez.

### `ExamPreparationScreen` (TUI)

- Presenta título, texto explicativo, rutas, estados y lista compacta.
- Reutiliza el patrón/controles de `LanguageList` y `LanguageSelection`.
- No contiene botones `Confirmar` / `Cancelar` de gran tamaño.
- Mantiene foco de teclado y permite volver al selector.
- Si el estado no está listo, explica bloqueos y no despacha `exam-init`.

Boceto español:

```text
┌ Preparar examen ───────────────────────────────────────────┐
│ Antes de comenzar configura el proyecto y el enunciado.    │
│                                                            │
│ Proyecto       ✓ /Users/.../DominoConquista                │
│ Instrucciones  ✓ /Users/.../examen.md                      │
│ Preflight      ✓ Proyecto Android y herramientas listas    │
│                                                            │
│ Configura con:                                              │
│   /project <ruta-del-proyecto>                              │
│   /instructions <ruta-del-enunciado.md>                     │
│                                                            │
│ > Empezar examen                                            │
│   Volver                                                    │
│                                                            │
│ ↑/↓ Mover · Enter Seleccionar · Esc Volver                 │
└────────────────────────────────────────────────────────────┘
```

Estados pendientes o inválidos deben ser visibles, por ejemplo:

```text
Proyecto       ✗ No configurado
Instrucciones  ✗ No configuradas
Preflight      — Pendiente
Estado         Faltan requisitos
```

El layout debe adaptarse a terminales pequeñas: texto con wrap, lista compacta,
sin alturas fijas excesivas. No reducir el área de conversación más de lo
necesario.

### Comandos `/project` y `/instructions`

Registrar ambos en el parser/command registry central. No añadir un parser
paralelo exclusivo para el TUI.

- `/project <ruta>` actualiza `SessionContext.project_path` o el campo canónico
  ya existente; revisar configuración actual antes de decidir el campo.
- `/instructions <ruta>` actualiza el campo canónico de statement/instructions
  del examen en el contexto existente. Si no existe, agregarlo al modelo de
  contexto de manera versionada y con persistencia compatible.
- Los comandos deben funcionar en TUI y CLI si el contrato compartido lo permite.
- Los mensajes de ayuda del selector y `/help` deben documentarlos.
- Los comandos no deben cambiar cwd.
- Los errores de ruta se devuelven como mensajes localizados y accionables.

Resolver rutas mediante `Path.expanduser()` y `Path.resolve()` (con política
explícita para rutas inexistentes); las relativas se anclan al cwd capturado al
recibir el comando. No resolver rutas relativas contra el directorio de
instalación ni contra `data_dir`.

### Inicio

El flujo de inicio usa un único servicio de aplicación que:

1. obtiene una instantánea de rutas;
2. comprueba identidad y examen activo;
3. ejecuta `ProjectPreflight`;
4. carga `ExamDefinition` desde la ruta Markdown;
5. valida definición;
6. solo entonces invoca `ExamineAction.start` / `ExamLifecycle.start`.

Evitar separar preflight de dispatch en un callback TUI que permita un cambio de
estado entre ambas operaciones. La validación final y creación del intento
deben ocurrir en una misma operación de aplicación, con protección contra doble
Enter/doble dispatch. `ExamineAction.start` debe reforzar precondiciones en el
límite de aplicación; no confiar exclusivamente en el TUI.

El modelo `ExamDefinition` sigue siendo autoritativo y conserva:

- `statement_format = markdown`;
- `statement_source` como ruta;
- `original_statement` verbatim;
- `original_source_path`;
- `requirements`;
- límites de tiempo/consultas;
- `rubric_ref` y `documentation_rules`;
- `limitations`.

No cambiar el algoritmo de normalización ni la regla de pesos funcionales.

### Temporizador

El dominio ya persiste `started_at` y `finished_at`; no añadir ticks a `ExamEvent`.

Componente visual sugerido `ExamStatusBar`:

```text
EXAMEN ACTIVO | Transcurrido 00:12:34 | Restante 00:47:26 | /ask 1/4
```

Sin límite:

```text
EXAMEN ACTIVO | Transcurrido 00:12:34 | /ask 1
```

Cálculo de presentación:

```python
elapsed = max(0, now_utc - attempt.started_at).total_seconds()
remaining = max(0, allowed_duration_seconds - elapsed)
```

Usar el reloj/servicio de tiempo inyectable existente para pruebas. La UI puede
usar el mecanismo periódico de Textual (`set_interval` o equivalente del
proyecto), solo para refrescar la etiqueta. No crear threads/timers propios si
el framework ya provee scheduler. El callback debe ser ligero y no hacer I/O,
LLM ni acceso bloqueante al store.

El timestamp persistido sigue siendo la fuente autoritativa. Al iniciar la UI
con un intento activo, leer el intento y reconstruir la etiqueta desde
`started_at`. Cuando se finaliza, detener la actualización y refrescar el footer.

El ask count se obtiene del intento/event log o del snapshot de estado que ya
mantenga el servicio; no consultar el store cada segundo. Actualizar el contador
cuando llegue un evento de ask completado.

## Flujo de estados

```text
IDLE
  └─ select exam-init → PREPARING
       ├─ escape → IDLE
       ├─ configure project/instructions → PREPARING (refresh status)
       └─ start
            ├─ validation failed → PREPARING (show blockers)
            └─ validation passed → ACTIVE
                 ├─ ask completed → ACTIVE (refresh ask count)
                 ├─ time limit reached → ACTIVE_EXPIRED (warning only)
                 └─ exam-finish → FINISHING → COMPLETED
```

`ACTIVE_EXPIRED` no es un estado de dominio nuevo necesariamente; puede ser una
condición derivada para la presentación. El examen sigue activo hasta la acción
de finalización.

## Finalización: progreso y entrega del informe

`ExamineAction.finish` orquesta etapas lentas. Para no dejarlas silenciosas, se
pasa un callback de progreso opcional desde el TUI (vía `Router.progress`) hasta
`EvidenceCollector`, que lo invoca antes de cada etapa real (`inspection`,
`build`, `unit_tests`, `lint`, `detekt`). `ExamineAction` emite además avance
para la interpretación del modelo y la generación del informe. El callback
recibe un identificador de etapa; la localización se resuelve con
`get_ui_string` usando el locale del intento. El TUI convierte cada mensaje en
un `OutputReady` (seguro entre hilos).

El informe se escribe con `ExamReportGenerator.generate(path=...)` apuntando a
`ExamDocs.path(REPORT_NAME)` dentro de `docs/ada-sensei/exams/<exam-slug>/`; el
generador no cambia su contrato. La apertura posterior usa
`ada_sensei.tools.opener.open_path` (best-effort, multiplataforma) y solo ocurre
en el TUI, condicionada por `tools.open_report`.

## Persistencia y compatibilidad

- Preferir campos existentes de configuración/contexto. No duplicar `project.path`.
- Añadir `instructions_path` solo si no hay campo canónico apropiado.
- Versionar cambios de contexto persistido y mantener lectura de registros
  anteriores.
- No alterar esquemas históricos de `ExamAttempt` salvo que la inspección
  demuestre que se necesita un dato que hoy no se conserva.
- `ExamAttempt.project_id`, `exam_id`, `started_at`, locale y límites siguen
  siendo snapshot del inicio.
- La definición se persiste al inicio; finish no vuelve a leer el archivo.

## Pruebas

- Unitarias de resolución de rutas, parser y validadores.
- TUI tests con el widget real: navegación teclado, focus, resize, selección,
  estados inválidos, panel sin botones grandes y cancelación.
- Integración de `/project`, `/instructions`, `exam-init`, `/ask`, `exam-finish`.
- Pruebas de reloj inyectado: sin límite, countdown, cero, overtime y resume.
- Doble Enter no crea dos intentos.
- CLI `--yes` no omite preflight.
- El PDF se escribe bajo `docs/ada-sensei/exams/<exam-slug>/report.pdf` y la
  ruta se expone en el resultado.
- Mensajes de progreso por etapa, sin efecto en el resultado.
- Apertura best-effort con toggle `tools.open_report`, sin fallo propagado.
- Regresión completa de scoring, eventos, PDF, persistencia, locale y
  `006-evaluate`.
