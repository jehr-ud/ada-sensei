# Requirements — Learning Path and Mastery

### RQ-LRN-001 Versioned subject catalog
The system SHALL load a versioned JSON learning catalog containing domain, stages,
competencies, prerequisites, exit challenges, and rubric references.

### RQ-LRN-002 Android default catalog
The default catalog SHALL contain the seven stages named in `android-learning-catalog.json`.

### RQ-LRN-003 First-run welcome
A student without a learning profile SHALL see the learning goal, seven stages,
and the choice to diagnose or choose a starting stage.

### RQ-LRN-004 Explicit starting stage
The student MAY choose a starting stage without diagnosis. The system SHALL NOT
mark skipped prerequisite stages as mastered.

### RQ-LRN-005 Two intents
The system SHALL support Study and Examine as separate intents. Examine can start
at any point and uses `/exam-init` and `/exam-finish`.

### RQ-LRN-006 Initial diagnostic
The initial diagnostic SHALL report baseline strengths, gaps, evidence confidence,
and a recommended starting stage without asserting mastery solely from self-report.

### RQ-LRN-007 Three assessment dimensions
Every stage exit assessment SHALL assess construction, analysis/design, and comprehension.

### RQ-LRN-008 Stage-specific criteria
The rubric SHALL resolve criteria from the selected stage's versioned JSON rubric.

### RQ-LRN-009 Configurable score scale
Rubric score scale, dimension weights, critical criteria, and gates SHALL be data-driven.

### RQ-LRN-010 Mastery gates
Default advancement SHALL require overall >=3.0/4, each dimension >=2.5/4,
critical criteria >=2.0/4, evidence in every dimension, exit challenge, and comprehension check.

### RQ-LRN-011 Insufficient evidence
Insufficient evidence SHALL produce `NOT_READY/INSUFFICIENT_EVIDENCE`, never inferred pass/fail.

### RQ-LRN-012 No compensation for critical gap
A high overall score SHALL NOT override a critical criterion below its threshold.

### RQ-LRN-013 Evidence-first decision
Progression SHALL be based on evidence, not completion, elapsed time, number of questions, or self-report alone.

### RQ-LRN-014 Equivalent reassessment
After remediation, the system SHALL provide an equivalent but non-identical exit challenge.

### RQ-LRN-015 Personalized practice
Recommended practice SHALL use stage, current gaps, recurring errors, and prior evidence and SHALL explain its relevance.

### RQ-LRN-016 Student may select another stage
A student MAY request another stage; unmet prerequisites SHALL be disclosed and not silently marked mastered.

### RQ-LRN-017 Persistence and versioning
Learning profile, plan, events, mastery assessments, and progression decisions SHALL be persisted with catalog/rubric/policy versions.

### RQ-LRN-018 Separate exam records
Formal exam records SHALL remain separate from mastery assessment and SHALL NOT automatically change stage.

### RQ-LRN-019 Domain independence
The mastery engine SHALL operate against generic JSON catalog/rubric contracts and SHALL NOT hard-code Android-specific criteria.

### RQ-LRN-020 Explainable decision
Every advancement decision SHALL report pass/fail status for each gate, evidence references, gaps, and recommended next activity.

### RQ-LRN-021 Assistance is not a penalty
The number of `/ask` calls SHALL NOT by itself reduce mastery score. Assistance events may inform context and must be reported where relevant.

### RQ-LRN-022 Audit trail
Instructor policy overrides and student stage selections SHALL be recorded as learning events.
