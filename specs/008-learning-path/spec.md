# Spec 008 — Learning Path and Mastery (Config-Driven)

## Objective

Define the learning journey, onboarding, stage-specific assessment criteria, and evidence-based progression independently of a specific subject. Learning stages, stage rubrics, and progression policy SHALL be loaded from the project's root `config/` directory rather than duplicated in application code or maintained as a separate hardcoded catalog.

## Configuration source of truth

The following root configuration files are expected, subject to verification against the repository:

- `config/stages.es.json`
- `config/stages.en.json`
- `config/stage-rubrics.es.json`
- `config/stage-rubrics.en.json`
- `config/progression-policy.es.json`
- `config/progression-policy.en.json`

`config/README.md` documents the configuration layout. OpenCode must inspect actual files and update this list if filenames differ.

The localized stage catalogs and rubric files SHALL represent the same learning model. Stable IDs, ordering, prerequisite relationships, rubric references, criterion IDs, weights, criticality, score scales, and progression semantics SHALL be equivalent across locales. Only student-facing presentation fields may differ by locale. The progression policy's machine behavior must not vary by language.

The `config/` directory SHALL be the authoritative source for stages, rubric definitions, and progression policy. The application MAY deserialize configuration into typed runtime models, but SHALL NOT silently replace missing or invalid configuration with duplicated hardcoded business rules.

## Student intents

- **Study:** learn, practice, ask questions, view examples, and request a stage exit assessment to determine readiness for the next stage.
- **Examine:** start and finish a formal examination independently of the current study stage using the existing exam workflow, such as `/exam-init` and `/exam-finish` if these are the actual registered commands.

A formal examination SHALL remain separate from mastery assessment and SHALL NOT silently advance the learning stage.

## First-run onboarding

When the student has no learning profile, ADA Sensei SHALL load the selected-locale stage catalog and show the learning goal, all configured stages in catalog order, and options to run an initial diagnostic or choose a starting stage.

The learning goal and stage labels/descriptions SHALL use the selected locale. The UI SHALL not hardcode a stage count; it SHALL derive the list from the validated catalog.

The chosen catalog ID/version, stage ID, locale, and diagnostic state SHALL be persisted as appropriate. Selecting a starting stage SHALL NOT mark skipped prerequisites as mastered.

## Learning catalog and prerequisites

The catalog loader SHALL resolve a validated catalog for the selected locale. Stage IDs are stable across locales. Prerequisites are a graph, not display-only text.

The loader SHALL validate at least:
- Unique catalog and stage IDs.
- Valid, unique stage ordering where required by the schema.
- All prerequisite IDs exist.
- No prerequisite cycles.
- All referenced rubric IDs exist in the corresponding rubric configuration.
- Required fields and supported schema versions are present.
- Locale variants have equivalent stage IDs, order, prerequisites, and rubric references.

If a catalog is invalid or missing, the system SHALL report a clear configuration error and SHALL NOT silently infer a default stage or mark stages mastered.

## Rubrics and mastery assessment

Every stage exit assessment SHALL evaluate the configured dimensions and criteria from the selected stage's rubric. The generic mastery engine SHALL consume rubric JSON and SHALL NOT hardcode Android/Kotlin criteria, weights, score thresholds, or critical criteria.

The existing default model uses three dimensions:
1. Construction.
2. Analysis and design.
3. Comprehension.

These dimensions and their weights are configuration data, not assumptions to hardcode in scoring code. The current configuration may use construction 0.4, analysis/design 0.3, and comprehension 0.3; the engine SHALL load and validate the configured values.

The assessment SHALL combine project/build/test/static-analysis evidence from the reusable evaluation engine, when available, with a structured comprehension or transfer check when required by the configured policy. LLM interpretation may map evidence to criteria but SHALL NOT fabricate tool evidence.

Missing evidence SHALL remain `NOT_EVALUATED`; it SHALL NOT be coerced to zero or treated as a pass. The configured policy may prevent advancement when required evidence is missing.

## Config-driven progression policy

The progression engine SHALL load thresholds and gates from the selected policy configuration. The currently supplied `mastery-default-v1` policy defines:
- Score scale 0–4.
- Minimum overall score 3.0.
- Minimum score of 2.5 for each dimension.
- Minimum score of 2.0 for each critical criterion.
- Evidence required for each dimension.
- Exit challenge required.
- Comprehension check required.
- Missing evidence means `NOT_EVALUATED` and no advancement.
- Asking questions is not automatically penalized.
- Assistance events may be recorded and reported.
- Instructor overrides must be explicit, versioned, and reported.

These are defaults from configuration, not constants to embed in the engine. If the config changes, the engine SHALL apply the validated new policy without code changes, provided the schema version remains supported.

All gates must pass for advancement. A high overall score SHALL NOT compensate for a failed critical criterion or a missing required evidence gate.

## Initial diagnostic and adaptive practice

The initial diagnostic SHALL establish a baseline, not declare mastery solely from self-report. It SHALL use the configured catalog and competencies to report evidence-backed strengths, gaps, confidence, and a recommended starting stage.

The Planner SHALL recommend practice using current stage, rubric gaps, recurring errors, and prior evidence. Recommendations SHALL explain their relevance. Repeated weaknesses SHOULD result in smaller prerequisite exercises or alternative explanations rather than merely harder challenges.

A student MAY select another stage. The system SHALL disclose unmet prerequisites and SHALL NOT mark skipped stages as mastered.

## Assessment and progression lifecycle

1. Load and validate the catalog, rubric configuration, and progression policy for the active locale.
2. Resolve the current stage and its rubric by stable IDs.
3. Collect relevant project evidence and required comprehension evidence.
4. Map available evidence to configured criteria.
5. Calculate criterion, dimension, and overall scores deterministically using configured scales and weights.
6. Evaluate each configured policy gate deterministically.
7. Persist assessment and progression decision with catalog, rubric, and policy versions.
8. Present gate outcomes, evidence references, gaps, and a recommended next activity.
9. If ready, offer transition to the next eligible stage. Apply any required student confirmation and persist the official stage transition only through the authorized progression component.
10. If not ready or evidence is insufficient, remain in the current stage and provide targeted remediation.

Formal exam records SHALL remain separate from mastery assessments and SHALL NOT automatically change the current stage.

## Localization

Locale selection SHALL affect labels, descriptions, learning goals, challenge presentation, rubric descriptions, and messages. It SHALL NOT affect stable IDs, score calculation, criterion identity, criticality, weights, thresholds, or progression outcomes.

The implementation SHALL use the selected locale's configuration files or an existing equivalent locale-aware loader. Missing locale files or keys SHALL follow the project's documented deterministic fallback and diagnostic behavior. It SHALL NOT invent translations for critical criteria at runtime.

## Persistence and auditability

Persist learning profile, learning plan, learning events, mastery assessments, and progression decisions under ADA Sensei's data directory, not inside the student's Android project.

Persist the catalog ID/version, rubric version, policy ID/version, stage ID, challenge ID, evidence references, and decision rationale required to reproduce and explain the result. Keep these records separate from formal exam attempts and generic project evaluation results.

Student stage selections and instructor policy overrides SHALL be auditable.

## Non-goals

This specification does not define a cloud LMS, automatic identity verification, or automatic mastery inference from question volume. It does not require every configured stage to be completed linearly when the catalog defines a different prerequisite graph.
