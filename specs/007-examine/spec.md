# Especificación — 007 Examine: flujo de inicio y sesión de examen

## Objetivo

Refactorizar la experiencia de `exam-init` para que el estudiante pueda preparar,
validar e iniciar un examen desde el TUI sin controles grandes que oculten el
enunciado ni dependan de botones de confirmación. El flujo debe ser guiado,
accesible por teclado, bilingüe y coherente con el selector de idioma existente.

El examen se define mediante un archivo de instrucciones del docente (Markdown
como formato recomendado) y se ejecuta sobre un proyecto Android configurado
explícitamente. No se crea ningún intento ni comienza el tiempo hasta que ambas
rutas hayan sido configuradas y validadas y el estudiante seleccione **Empezar
examen**.

## Alcance

Incluye:

- comandos `/project <ruta>` y `/instructions <ruta>`;
- selección de `Iniciar examen` desde el selector de acciones;
- pantalla/panel de preparación con instrucciones claras y estado de requisitos;
- reemplazo de botones grandes Confirmar/Cancelar por una lista compacta de
  opciones navegable con Arriba/Abajo/Enter/Esc, siguiendo el patrón visual y
  de interacción del selector de idioma;
- preflight obligatorio del proyecto y validación de las instrucciones;
- inicio explícito del examen;
- temporizador visible durante el examen;
- traducciones `es-CO` y `en-US`.

No cambia el motor de evaluación, la rúbrica, el modelo `ExamDefinition`, la
recolección de evidencias, el cálculo de notas, la generación del PDF ni las
reglas de integridad ya definidas en este spec.

## Flujo principal

```text
Selector de acciones
  └─ Iniciar examen
       ↓
Panel de preparación (no hay intento activo)
  ├─ Mostrar ruta del proyecto: configurada / pendiente / inválida
  ├─ Mostrar archivo de instrucciones: configurado / pendiente / inválido
  ├─ Mostrar resultado de preflight del proyecto
  ├─ Mostrar instrucciones para configurar:
  │    /project <ruta-del-proyecto>
  │    /instructions <ruta-del-enunciado.md>
  └─ Opciones compactas:
       > Empezar examen
         Volver
       ↓ Enter
       Validar todo de nuevo
       ├─ Hay errores → permanecer en preparación y mostrar todos los errores
       └─ Todo válido
            ↓
          Resolver ExamDefinition
            ↓
          Crear ExamAttempt y documentación
            ↓
          Iniciar cronómetro y mostrar sesión activa
```

## Comportamiento esperado del TUI

### Panel de preparación

Al seleccionar `Iniciar examen`, el TUI debe mostrar un panel de preparación
compacto. No debe presentar botones rectangulares grandes ni controles que
ocupen una fila completa. Debe reutilizar el patrón de selector del idioma:
opciones de texto en una lista, cursor `>` para indicar selección y ayuda de
teclado al pie.

El panel debe conservar visible el área de salida y no desplazar ni ocultar el
texto que el usuario ya escribió. No debe exigir que el estudiante pegue el
enunciado completo en el área de texto.

Contenido mínimo, localizado:

- Título: `Preparar examen` / `Prepare exam`.
- Explicación breve: antes de comenzar, configura el proyecto Android y el
  archivo Markdown con las instrucciones del docente.
- Proyecto: ruta actual o `No configurado`; mostrar si existe y si pasa el
  preflight.
- Instrucciones: ruta actual o `No configuradas`; mostrar si el archivo existe,
  es legible y se puede resolver como `ExamDefinition`.
- Estado general: `Listo para comenzar` o `Faltan requisitos`.
- Ayuda:
  - `/project <ruta>` — configurar el directorio raíz del proyecto Android.
  - `/instructions <ruta>` — configurar el archivo de instrucciones del examen.
- Opciones:
  - `Empezar examen`
  - `Volver`

Las opciones deben comportarse como una lista seleccionable equivalente a
`LanguageList`: Arriba/Abajo cambia la selección, Enter ejecuta la opción,
Escape vuelve al selector principal. La selección inicial será `Empezar examen`.
Si los requisitos no están completos, esa opción se muestra deshabilitada o,
si la biblioteca TUI no permite deshabilitar elementos, se puede seleccionar
pero debe explicar los bloqueos sin ejecutar ninguna acción.

### No iniciar automáticamente

Abrir el panel de preparación no inicia el examen. No se crea intento, evento
`EXAM_STARTED`, carpeta de documentación ni cronómetro al seleccionar la acción
en el selector. Solamente la selección explícita de `Empezar examen`, después de
validar los requisitos, puede iniciar el examen.

### Validación al empezar

Al seleccionar `Empezar examen`, ejecutar nuevamente todas las validaciones
para evitar usar resultados obsoletos:

1. Existe una identidad de estudiante configurada.
2. `/project` apunta a una ruta existente y es un directorio.
3. El directorio corresponde a un proyecto Android: contiene manifest y archivo
   de build Gradle reconocibles por los detectores existentes.
4. Gradle/Gradle Wrapper, JDK 17+ y Android SDK están disponibles conforme al
   `ProjectPreflight` existente.
5. `/instructions` apunta a un archivo regular, existente y legible.
6. El `ExamDefinitionLoader` puede cargar el archivo y producir una definición
   válida, incluyendo validaciones de ids y pesos funcionales.
7. No existe otro examen activo en la sesión.

El preflight debe ser de solo lectura: no ejecutar Gradle, no compilar, no
modificar el proyecto. La validación no debe crear `ExamAttempt`, timer ni
documentación. Si falla, presentar todos los errores conocidos, mantener el
panel abierto y permitir corregir rutas mediante los comandos.

Si todo es válido, pedir confirmación únicamente mediante la opción
`Empezar examen` ya seleccionada. No volver a presentar un segundo diálogo con
botones Confirmar/Cancelar.

## Comandos de configuración

### `/project <ruta>`

Configura la raíz del proyecto que se examinará.

- Acepta ruta absoluta o relativa.
- Las rutas relativas se resuelven respecto al directorio de trabajo actual del
  proceso, no respecto a la carpeta de instalación de ADA Sensei.
- Normaliza `~` y la ruta resultante.
- Guarda la ruta en el contexto/configuración de sesión existente.
- No debe cambiar el directorio actual del proceso.
- Debe mostrar la ruta resuelta y un estado preliminar (directorio existente,
  estructura Android detectada o pendiente de preflight).
- No crea ni inicia un examen.
- Sin argumento, puede mostrar la ruta actualmente configurada si el contrato
  CLI existente permite comandos informativos; no inventar una ruta por defecto.

### `/instructions <ruta>`

Configura el archivo de instrucciones del docente.

- Acepta ruta absoluta o relativa; las relativas se resuelven desde el directorio
  de trabajo actual del proceso.
- Formato requerido para esta iteración: `.md` (Markdown).
- Valida que sea archivo regular, legible y con contenido no vacío.
- La carga definitiva se realiza con `ExamDefinitionLoader`; no duplicar ni
  reimplementar el parser.
- Conserva `statement_source`, `original_statement` y
  `original_source_path` según el modelo `ExamDefinition`.
- No copia ni modifica el archivo del docente.
- No inicia examen.
- Sin argumento, puede mostrar la ruta configurada si el contrato CLI lo admite.

Los dos comandos son configuración de contexto. No sustituyen ni duplican
`ExamDefinitionLoader`, `ProjectPreflight`, `ExamLifecycle` o `ExamineAction`.

## Examen activo y temporizador

Después de iniciar correctamente:

- mostrar un indicador persistente y compacto en el encabezado o barra de
  estado del TUI;
- mostrar tiempo transcurrido en formato `HH:MM:SS`;
- si `allowed_duration_seconds` existe, mostrar también tiempo restante y
  estado de vencimiento; por ejemplo `Restante 00:42:15`;
- si no hay límite de duración, mostrar tiempo transcurrido y no inventar un
  countdown;
- mostrar el contador de consultas exitosas `/ask` respecto al límite, si está
  definido: `Consultas 1/4`; si no hay límite, `Consultas 1`;
- actualizar la presentación periódicamente sin bloquear la entrada, el
  selector ni los workers;
- al terminar el examen, retirar el indicador activo y conservar la duración
  final en el resultado/resumen.

El temporizador visual es una proyección de `started_at` y de la hora actual.
La fuente de verdad persistida continúa siendo `started_at`/`finished_at` y la
duración calculada por el dominio. No persistir ticks ni usar el contador visual
como evidencia. Al reanudar una sesión, recalcular el tiempo desde el timestamp
persistido; no reiniciar el reloj.

Si se alcanza el límite de duración, mostrar claramente `Tiempo agotado` /
`Time limit reached`. No finalizar ni modificar el proyecto silenciosamente.
La política de finalización automática no se introduce en esta refactorización:
el estudiante debe usar `Finalizar examen`; la duración real y el overtime se
calculan al finalizar.

## Finalización

`Finalizar examen` conserva el flujo de finalización y confirmación de dominio
existente. La interfaz puede adoptar el mismo selector compacto de opciones
`Finalizar examen` / `Continuar`, sin botones grandes, pero no debe cambiar la
semántica de `ExamFinishInput.confirmed`, el cierre de eventos `/ask` ni la
recolección de evidencias.

### Progreso de finalización

La finalización ejecuta varias etapas lentas (hasta cuatro invocaciones de
Gradle con timeout configurable, interpretación del modelo y generación del
informe). Para que el estudiante no perciba que la operación se colgó, el TUI
emite mensajes de avance localizados, uno por etapa real del pipeline:

- inspección del proyecto;
- build de Gradle;
- pruebas unitarias;
- Android Lint;
- Detekt;
- interpretación del modelo;
- generación del informe PDF.

Los mensajes se originan en la etapa que realmente se está ejecutando (callback
del pipeline de evidencias), nunca en un temporizador simulado, y no alteran el
resultado, la puntuación ni el orden de ejecución. La etapa actual también puede
reflejarse en el indicador de estado.

### Entrega del informe

El informe PDF se escribe dentro del proyecto examinado, en el subárbol propio
`docs/ada-sensei/exams/<exam-slug>/report.pdf`, junto a la documentación
generada del examen (RQ-EXM-024). No se escribe en el directorio de datos de
ADA Sensei. La escritura respeta la integridad del proyecto: solo ocurre dentro
de `docs/ada-sensei/`.

Tras generarlo, el TUI lo abre con el visor del sistema de forma best-effort,
controlado por el ajuste `tools.open_report` (por defecto activado). Si no hay
visor disponible, la apertura falla en silencio y el resultado no cambia. El
CLI no interactivo no abre el PDF: solo imprime la ruta.

## Persistencia y seguridad

- Persistir las rutas de proyecto e instrucciones en el contexto/configuración
  existente con el alcance de sesión ya definido; no crear un almacén paralelo
  sin necesidad.
- Persistir la definición resuelta al iniciar, de modo que finalizar no dependa
  de volver a leer el archivo original.
- No guardar el contenido del proyecto ni copiar el enunciado al proyecto.
- No modificar fuentes del estudiante ni el archivo de instrucciones. La única
  escritura en el proyecto es la documentación y el informe generados bajo
  `docs/ada-sensei/` (RQ-EXM-009, RQ-EXM-024).
- Si la ruta cambia durante un examen activo, no cambiar el `project_root` del
  intento actual. El intento conserva el `project_id` y el proyecto resueltos
  al inicio. Un cambio de ruta solo afecta al siguiente examen.
- Los errores de rutas deben mostrarse sin trazas internas ni secretos.

## Internacionalización

Todas las cadenas nuevas deben existir en `es-CO` y `en-US`, con fallback
determinista `en-US`. El idioma se obtiene del servicio de locale existente.
No duplicar selector ni catálogo de idiomas.

## Fuera de alcance

- Crear un selector gráfico de carpetas/archivos.
- Cambiar la rúbrica o ponderaciones.
- Cambiar la lógica de puntuación o evaluación.
- Implementar exámenes sin proyecto Android.
- Ejecutar pruebas instrumentadas `connectedAndroidTest`.
- Forzar cierre automático al vencer el tiempo.
- Cambiar la arquitectura de agentes o enrutar acciones a nuevos agentes.

## Criterios de aceptación

1. Seleccionar `Iniciar examen` abre el panel de preparación, no un panel con
   botones grandes Confirmar/Cancelar.
2. El panel se parece en interacción al selector de idioma: lista compacta,
   cursor `>`, Arriba/Abajo/Enter/Escape.
3. El panel explica con claridad cómo configurar `/project <ruta>` y
   `/instructions <ruta>`.
4. No se puede iniciar si falta cualquiera de las dos rutas.
5. No se puede iniciar con ruta de proyecto inexistente, archivo no Android,
   herramientas requeridas ausentes o archivo de instrucciones inválido.
6. Todos los errores detectados se muestran en el idioma activo; el panel sigue
   disponible para corregir la configuración.
7. Abrir el panel, validar o cancelar no crea intento, timer, eventos ni docs.
8. `Empezar examen` crea exactamente un intento y registra el inicio una sola
   vez.
9. El panel de examen activo muestra tiempo transcurrido; muestra tiempo
   restante solo cuando existe límite.
10. El temporizador no bloquea el TUI y al reanudar usa el timestamp persistido.
11. El contador `/ask` continúa derivándose de eventos de aplicación y no de
    texto de terminal.
12. `/exam-finish` sigue generando el resultado/PDF con las reglas existentes;
    el PDF se escribe en `docs/ada-sensei/exams/<exam-slug>/report.pdf` del
    proyecto.
13. Durante la finalización se muestran mensajes de avance por etapa.
14. Con `tools.open_report` activado, el TUI abre el PDF generado; si la
    apertura falla, el resultado no se ve afectado.
15. Las acciones CLI directas siguen funcionando y validan precondiciones antes
    de crear estado. No se permite que `--yes` omita `ProjectPreflight`.
16. Las pruebas existentes de `006-evaluate`, el motor de examen, persistencia,
    idioma y selector TUI continúan pasando.
