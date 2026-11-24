# ADR-029 — Reporte único de evaluación y PDF auditable

- Estado: Aceptado e implementado
- Contexto: el informe puede presentar cifras y conclusiones inconsistentes cuando varias capas recalculan o narran resultados.
- Decisión: `EvaluatorAgent` produce un único `EvaluationReport`; TUI, persistencia y PDF consumen el mismo objeto. El PDF no evalúa ni calcula.
- Consecuencia: cada decisión debe incluir evidencia localizable; una reevaluación crea una revisión vinculada y no sobrescribe silenciosamente el resultado previo.
- Verificación: `tests/exams/test_report.py`, `tests/exams/test_evaluation_report.py` y `tests/evaluation/test_v2_evaluators.py` comprueban consistencia entre contrato, presentación y PDF, incluido el límite de cuatro páginas.
- Limitación: el enlace `supersedes_report_id` ya se preserva, pero el comando
  completo de reevaluación y la fixture automatizada de Domino aún no están
  cubiertos.
