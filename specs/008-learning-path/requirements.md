# Requirements — Spec 008 Learning Path (Config-Driven)

### RQ-LRN-001 — Versioned configuration
The system SHALL load and validate versioned stage catalogs, rubric definitions, and progression policies from the root `config/` directory or an explicitly configured equivalent path.

### RQ-LRN-002 — Config is the source of truth
Stage content, ordering, prerequisites, exit challenges, rubric references, criteria, weights, criticality, score scales, thresholds, and progression gates SHALL come from validated configuration, not duplicated hardcoded application rules.

### RQ-LRN-003 — Localized catalog
The system SHALL support the configured Spanish and English catalogs. Locale variants SHALL share stable IDs and equivalent learning and assessment semantics.

### RQ-LRN-004 — Dynamic onboarding
A first-run student SHALL see the learning goal and all stages from the validated catalog in catalog order, then choose diagnosis or a starting stage. The UI SHALL derive the number of stages from configuration.

### RQ-LRN-005 — Explicit starting stage
The student MAY choose a starting stage without diagnosis. The system SHALL disclose unmet prerequisites and SHALL NOT mark skipped stages as mastered.

### RQ-LRN-006 — Separate intents
The system SHALL support Study and Examine as separate intents. Formal exams use the actual registered exam workflow and SHALL NOT automatically change stage mastery or progression.

### RQ-LRN-007 — Configured assessment dimensions
The mastery engine SHALL load assessment dimensions, weights, criteria, criticality, score scale, and thresholds from the selected stage's rubric configuration.

### RQ-LRN-008 — Reusable evaluation evidence
The mastery workflow SHALL reuse the existing evaluation engine for project evidence where appropriate and SHALL combine it with required comprehension/transfer evidence defined by the policy or rubric.

### RQ-LRN-009 — Deterministic scoring
Criterion, dimension, overall scores, and policy gates SHALL be calculated deterministically from validated configuration and collected evidence. LLMs SHALL NOT determine scores or progression by unrestricted free-form output.

### RQ-LRN-010 — Configured mastery gates
The current default policy SHALL be read from `config/progression-policy.{es,en}.json`. The engine SHALL apply all configured gates; it SHALL NOT hardcode the current numeric defaults.

### RQ-LRN-011 — Insufficient evidence
Missing evidence SHALL remain `NOT_EVALUATED` and SHALL NOT be coerced to zero, pass, or failure. If required evidence is missing, the system SHALL prevent advancement according to the configured policy.

### RQ-LRN-012 — Critical criteria
A high overall score SHALL NOT override a critical criterion below its configured threshold.

### RQ-LRN-013 — Evidence-first decision
Progression SHALL be based on evidence and configured gates, not completion, elapsed time, question count, or self-report alone.

### RQ-LRN-014 — Equivalent reassessment
After remediation, the system SHALL provide an equivalent but non-identical exit challenge when required by the configured assessment policy.

### RQ-LRN-015 — Personalized practice
Recommended practice SHALL use stage, current gaps, recurring errors, and prior evidence and SHALL explain its relevance.

### RQ-LRN-016 — Runtime config validation
The system SHALL reject or clearly report malformed JSON, unsupported schema versions, duplicate IDs, missing references, prerequisite cycles, invalid weights, and invalid thresholds. It SHALL NOT silently fall back to hardcoded learning rules.

### RQ-LRN-017 — Versioned persistence
Learning profile, plan, events, mastery assessments, and progression decisions SHALL persist relevant catalog, rubric, and policy versions so decisions can be explained and reproduced.

### RQ-LRN-018 — Separate exam records
Formal exam records SHALL remain separate from mastery assessment and SHALL NOT automatically change stage.

### RQ-LRN-019 — Domain independence
The mastery engine SHALL operate against generic catalog/rubric/policy contracts and SHALL NOT hardcode Android-specific criteria.

### RQ-LRN-020 — Explainable decision
Every progression decision SHALL report each gate result, evidence references, gaps, policy version, and recommended next activity.

### RQ-LRN-021 — Assistance is not a penalty
The number of `/ask` calls SHALL NOT by itself reduce mastery score. Assistance events MAY inform context and SHALL be reported where relevant according to configuration.

### RQ-LRN-022 — Audit trail
Instructor policy overrides and student stage selections SHALL be recorded as learning events.

### RQ-LRN-023 — Locale-independent decisions
Changing locale SHALL NOT change stable stage/criterion IDs, scores, rubric semantics, or progression decisions for equivalent evidence.

### RQ-LRN-024 — Config reload and precedence
The application SHALL document when configuration is loaded and whether it is reloaded during a process. The root `config/` files SHALL take precedence over packaged or legacy duplicate catalogs, unless the repository already defines an explicit deployment override. Any override SHALL be documented and testable.
