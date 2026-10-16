# Design — Learning Path and Mastery from Root Config

## Components

- `LearningCatalogLoader`: loads and validates localized stage catalog JSON from root `config/`.
- `RubricDefinitionLoader`: loads and validates locale-specific rubric JSON.
- `ProgressionPolicyLoader`: loads and validates the configured policy, using the selected locale path or the repository's documented shared-policy arrangement.
- `LearningProfileStore`, `LearningPlanStore`, `MasteryAssessmentStore`, and learning-event/progression stores.
- `DiagnosticService`: establishes a baseline, not a mastery decision.
- `MasteryAssessmentService`: assembles exit challenge, evidence, and rubric request.
- `ProgressionPolicyEngine`: deterministic gate evaluation using loaded policy values.
- `LearningPlanner`: selects next stage/activity from prerequisites and evidence.
- `LocaleResolver`: maps the selected UI locale to the correct config file and localized presentation fields, reusing the existing localization mechanism.

Use existing equivalent components if present; these names describe responsibilities, not a requirement to duplicate classes.

## Configuration layout

Expected files:
```text
config/
  stages.es.json
  stages.en.json
  stage-rubrics.es.json
  stage-rubrics.en.json
  progression-policy.es.json
  progression-policy.en.json
  README.md
```

Inspect the real files before implementing. If progression policy files differ only in presentation or are semantically identical, the implementation MAY share one language-neutral policy internally, but it must preserve the expected compatibility and document the choice. A locale-specific file must not alter scoring semantics.

## Loading and validation

1. Resolve locale using the existing settings/profile locale (`es-CO` or `en-US`).
2. Resolve the matching stage catalog and rubric configuration.
3. Resolve the applicable progression policy.
4. Parse JSON into typed models.
5. Validate schema versions, unique IDs, ordering, prerequisite references and acyclic graph, rubric references, rubric dimension weights, score scales, and policy thresholds.
6. Verify locale parity: stable IDs, stage order, prerequisites, rubric IDs, dimension IDs, criterion IDs, weights, critical flags, thresholds, and policy gates are equivalent across locales.
7. Fail clearly on invalid required configuration. Do not silently replace it with hardcoded defaults.
8. Record catalog/rubric/policy identifiers and versions in assessments and decisions.

Do not assume the path is the process working directory. Use the repository's existing config path resolver or a deterministic project-root/config resolver, and test invocation from different working directories.

## Generic contracts

`LearningStage`: stable `id`, `order`, localized title/goal, competencies, prerequisites, exit challenge, rubric ID.

`RubricDefinition`: stable rubric ID/version, dimensions, weights, criteria, critical flags, criterion scale, and configured thresholds.

`ProgressionPolicy`: stable policy ID/version, score scale, gates, retry policy, missing-evidence semantics, assistance policy, and versioned overrides where supported.

`MasteryAssessment`: ID, student/project/stage IDs, challenge ID, catalog version, rubric version, policy version, dimension and criterion scores, evidence references, limitations, and timestamp.

`ProgressionDecision`: decision ID, student ID, source/target stage IDs, status, gate results, reasons, recommended activity, policy version, and assessment ID.

Missing criterion evidence is `NOT_EVALUATED`, never coerced to zero. Normalization behavior must be defined once and tested. Required-evidence gates prevent advancement when evidence is incomplete.

## Scoring and decision flow

1. Load and validate active catalog, rubric, and policy.
2. Resolve stage by stable ID and rubric by configured reference.
3. Collect project/build/test/static-analysis evidence using the reusable `006-evaluate` engine where appropriate.
4. Collect structured comprehension/transfer evidence when required by the loaded policy.
5. Map evidence to configured criteria; LLM interpretation may assist mapping but cannot fabricate tool evidence.
6. Calculate scores deterministically using configured weights and scale.
7. Evaluate all policy gates deterministically.
8. Persist assessment and decision before presenting results.
9. If ready, offer transition to next eligible stage; only the authorized progression component commits the stage change.
10. If not ready or evidence is insufficient, explain criterion-level gaps and recommend targeted practice.

## Locale behavior

Locale selects presentation strings and file variants. It does not affect IDs or scoring. If translations are missing, use the documented deterministic fallback and diagnostics. Do not ask an LLM to improvise critical rubric translations.

## Config precedence and lifecycle

The root `config/` directory is the default authoritative source during local development. The loader must use a deterministic root resolver, not rely on the shell's current working directory. If the application packages config resources for deployment, define and test explicit precedence; do not silently let stale packaged copies override root config.

Document whether config is loaded once at startup or refreshed. If reload is supported, validate the new configuration fully before replacing the active in-memory version.

## Tests

- JSON/schema validation and malformed-file errors.
- Locale parity and stable identifiers.
- Root path resolution independent of current working directory.
- Config changes affect stage/rubric/policy behavior without source-code changes.
- Invalid config never silently falls back to hardcoded business rules.
- Deterministic scoring, missing evidence, critical gates, and boundary thresholds.
- Persistence round-trip and version audit.
- Exam records remain separate from mastery decisions.
