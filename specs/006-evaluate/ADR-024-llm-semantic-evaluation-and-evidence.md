# ADR-024 — Evaluación semántica LLM con evidencia verificable

- Estado: Aceptado e implementado
- Contexto: los requisitos funcionales y arquitectónicos requieren interpretación semántica; los analizadores deterministas no bastan.
- Decisión: el LLM decide estados por criterio dentro del EvidenceContext; el ScoreCalculator calcula la nota. El LLM no inventa evidencia ni calcula notas.
- Modelo inicial: `qwen2.5-coder:7b` vía Ollama, temperatura 0, tres intentos totales; proveedor, modelo, prompt, versión, duración y validación se persisten en `llm_runs`.
- Consecuencia: evaluación más contextual, con validación estricta de referencias y estados NOT_EVALUATED ante falta de evidencia.
- Verificación: `tests/evaluation/test_v2_evaluators.py` cubre salida inválida, evidencia inventada/rango inválido, cliente ausente, cobertura arquitectónica y estado bloqueado.
