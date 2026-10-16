# Design — 0010 Language Selection

## Preference
Persist `locale`, `locale_source`, and `updated_at` in the student settings/profile.

## Runtime resolution
Saved locale → validate supported locale → load matching catalog/rubric/policy → inject locale into TeacherAgent context → propagate to all subagents → render user-facing output.

## Invariants
- Locale identifiers: `es-CO`, `en-US`.
- IDs, scores, weights, critical flags, evidence requirements and decision enums are locale-independent.
- Missing translations use a deterministic fallback and emit a diagnostic.
- LLM-generated translations must not define rubric criteria or change progression policy.

## First-run UI
A compact screen with `Español` and `English`. After selection, show the welcome objective, seven/eight configured stages from the active catalog, and the choices to run a diagnostic or select a starting stage.

## Exam consistency
`exam-init` snapshots the active locale into the exam attempt. `exam-finish` uses that snapshot for messages and the report.
