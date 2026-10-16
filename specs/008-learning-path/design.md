# Design — Learning Path and Mastery

## Components

- `LearningCatalogLoader`: loads and validates subject catalog JSON.
- `RubricDefinitionLoader`: loads rubric JSON and validates dimensions/weights.
- `LearningProfileStore`, `LearningPlanStore`, `MasteryAssessmentStore`.
- `DiagnosticService`: creates a baseline profile, not a mastery decision.
- `MasteryAssessmentService`: assembles exit challenge, evidence, and rubric request.
- `ProgressionPolicyEngine`: deterministic gate evaluation.
- `LearningPlanner`: selects next stage/activity from prerequisites and evidence.

## Generic contracts

`LearningStage`: `id`, `order`, `title`, `goal`, `competencies`, `prerequisites`,
`exit_challenge`, `rubric_id`.

`MasteryAssessment`: `id`, `student_id`, `project_id`, `stage_id`, `challenge_id`,
`catalog_version`, `rubric_version`, `policy_version`, `dimension_scores`,
`criterion_scores`, `evidence_refs`, `limitations`, `created_at`.

`ProgressionDecision`: `decision_id`, `student_id`, `from_stage_id`, `to_stage_id`,
`status` (`READY`, `NOT_READY`, `INSUFFICIENT_EVIDENCE`), `gate_results`,
`reasons`, `recommended_activity`, `policy_version`, `assessment_id`.

Criterion scores are 0–4 or `not_evaluated`; never coerce missing evidence to 0.
Dimension and overall scores are normalized over evaluated criteria only, but the
policy's required-evidence gate prevents advancement when a required dimension or
critical criterion is missing. Implementations must define this normalization
once and test boundary cases.

## Decision algorithm

1. Validate catalog, rubric, and policy versions.
2. Collect evidence using the reusable `EvaluationEngine` from `006-evaluate` for
   project criteria, plus a structured comprehension check for explanation/transfer.
3. Map evidence to stage criteria; LLM interpretation is explicitly marked and
   cannot fabricate tool evidence.
4. Calculate criterion/dimension/overall scores deterministically.
5. Evaluate each policy gate deterministically.
6. Persist the assessment and decision before presenting the result.
7. If ready, offer transition to the next eligible stage; do not change stage until
   the student confirms if the UI policy requires confirmation.
8. If not ready, present criterion-level gaps and a targeted practice recommendation.

## Evidence channels

- project/build/test/static analysis evidence from `006-evaluate`;
- generated or curated exit challenge outputs;
- student explanation, prediction, debugging, and code modification;
- instructor-provided evidence only when catalog policy explicitly supports it.

Chat text alone cannot prove construction. Project artifacts alone do not prove
comprehension; the comprehension check is mandatory by default.

## JSON extensibility

A new subject adds a catalog and rubrics, not new progression-engine code. JSON
schema validation checks unique ids, prerequisite references, acyclic graph,
weights summing to 1.0 per rubric, valid thresholds, and rubric references.
