# ADR-027 — Entrega del informe de examen y progreso de finalización

## Estado
Propuesto

## Contexto

La finalización de un examen ejecuta hasta cuatro invocaciones de Gradle
(`build`, pruebas unitarias, Android Lint, Detekt), la interpretación del modelo
y la generación del PDF. En un proyecto Android real esto puede tardar varios
minutos y el TUI solo mostraba el estado `Examining…`, sin señales de avance, lo
que el estudiante percibe como un cuelgue.

Además, el informe PDF se escribía en el directorio de datos de ADA Sensei
(`~/.local/share/ada-sensei/reports/exams/`). El instructor necesita el informe
junto al proyecto evaluado, y el estudiante espera poder abrirlo al terminar.

La documentación generada del examen (`README`, contexto, rúbrica, arquitectura,
resumen) ya se escribe en el subárbol propio `docs/ada-sensei/exams/<slug>/` del
proyecto (RQ-EXM-009). El PDF era el único artefacto del examen fuera del
proyecto.

## Decisión

1. **Progreso real por etapa.** `ExamineAction.finish` recibe un callback de
   progreso opcional. El `EvidenceCollector` lo invoca antes de cada etapa real
   (`inspection`, `build`, `unit_tests`, `lint`, `detekt`); la acción emite
   además avance para la interpretación y el informe. La localización se resuelve
   con el locale del intento. No se simula progreso con temporizadores.

2. **Informe dentro del proyecto.** El PDF se escribe en
   `docs/ada-sensei/exams/<exam-slug>/report.pdf`, junto al resto de la
   documentación generada. Se conserva `ExamReportGenerator` sin cambios: el
   llamador pasa la ruta explícita. Se modifica RQ-EXM-024.

3. **Apertura best-effort.** El TUI abre el PDF con el visor del sistema
   (`open`/`xdg-open`/`start`) tras generarlo, controlado por el ajuste
   `tools.open_report` (por defecto activado). Un fallo de apertura nunca afecta
   al resultado. El CLI no interactivo no abre el PDF.

## Consecuencias

- El estudiante ve avance durante la finalización y sabe que el proceso sigue
  vivo.
- El informe queda junto al proyecto evaluado, lo que facilita la revisión por
  parte del instructor.
- El informe (con la nota sugerida) reside en el árbol del estudiante; es
  responsabilidad del flujo de entrega tratarlo como artefacto de evaluación. Se
  mantiene la regla de escribir solo bajo `docs/ada-sensei/`.
- El motor de scoring, los modelos de resultado y el contrato de
  `ExamReportGenerator` permanecen intactos.
- El progreso y la apertura son aditivos: no cambian la puntuación ni el orden
  de ejecución de la evaluación.


## Adenda 2026-11-20 — contenido y responsabilidad del informe

El informe PDF se genera desde `EvaluationReport` estructurado por `EvaluatorAgent`.
No se usa `ExamInterpretationAgent` para redactar contenido oficial ni calcular
notas. `TeacherAgent` consume el mismo resultado para tutoría y no puede editarlo.
El generador presenta las tablas R1–R12 definidas en la adenda normativa.
