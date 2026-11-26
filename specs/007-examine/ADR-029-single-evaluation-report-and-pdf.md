# ADR-029 — Reporte único de evaluación y PDF auditable

- Estado: Aceptado e implementado
- Contexto: el informe puede presentar cifras y conclusiones inconsistentes cuando varias capas recalculan o narran resultados.
- Decisión: `EvaluatorAgent` produce un único `EvaluationReport`; TUI, persistencia y PDF consumen el mismo objeto. El PDF no evalúa ni calcula, se pagina según el contenido y se persiste el reporte antes de intentarlo.
- Consecuencia: cada decisión debe incluir evidencia localizable; una reevaluación crea una revisión vinculada y no sobrescribe silenciosamente el resultado previo. Un fallo del PDF conserva el reporte y su estado terminado; el reintento reutiliza ese mismo reporte sin nueva evaluación ni resultados duplicados.
- Verificación: `tests/exams/test_report.py`, `tests/exams/test_evaluation_report.py`, `tests/exams/test_exams_structured_output.py`, `tests/exams/test_report_pagination.py`, `tests/exams/test_finish_pdf.py` y `tests/evaluation/test_v2_evaluators.py` comprueban consistencia entre contrato, interpretación, presentación, paginación y PDF.
- Limitación: el enlace `supersedes_report_id` ya se preserva, pero el comando
  completo de reevaluación y la fixture automatizada de Domino aún no están
  cubiertos.
