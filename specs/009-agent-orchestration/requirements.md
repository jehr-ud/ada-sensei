# Requirements — Agent Orchestration

### RQ-AGT-001 Principal Teacher
Every student-facing action SHALL enter through TeacherAgent, which owns intent interpretation, orchestration, and the final response.

### RQ-AGT-002 Three specialist agents
The system SHALL define PlannerAgent, EvaluatorAgent, and TrainerAgent with the responsibilities in `spec.md`.

### RQ-AGT-003 Mandatory participation
Every student-facing action SHALL invoke each specialist exactly once per orchestration cycle; a specialist may return typed `not_applicable` with rationale.

### RQ-AGT-004 Planner progression ownership
PlannerAgent SHALL track stage evidence and apply the configured mastery policy but SHALL NOT infer mastery from missing evidence or chat volume.

### RQ-AGT-005 Evaluator diagnostic ownership
EvaluatorAgent SHALL coordinate initial diagnostics, in-stage diagnostics, stage exit assessment evidence, and exam evaluation.

### RQ-AGT-006 Trainer teaching ownership
TrainerAgent SHALL provide stage-aligned explanations, examples, doubt resolution, hints, and adaptive practice using existing actions.

### RQ-AGT-007 Existing action reuse
The orchestration layer SHALL reuse AskAction, PracticeAction, ExamplesAction, EvaluateAction/EvaluationEngine, ExamInitAction, and ExamFinishAction without shelling out to the CLI or recursively invoking commands.

### RQ-AGT-008 First-run orchestration
The welcome flow SHALL use Teacher, Evaluator, Planner, and Trainer to perform onboarding and present diagnostic/stage choices.

### RQ-AGT-009 Study intent
Study intent SHALL support learn, practice, ask/examples, and explicit mastery evaluation as separate flows.

### RQ-AGT-010 Examine intent
Examine intent SHALL support exam-init and exam-finish at any stage and SHALL remain separate from automatic stage progression.

### RQ-AGT-011 Typed outputs
Every specialist output SHALL conform to a role-specific schema and include status, summary, payload, evidence references, uncertainties, and optional next step.

### RQ-AGT-012 Evidence integrity
Agents SHALL NOT fabricate evidence identifiers, test/build outcomes, or student performance observations.

### RQ-AGT-013 Deterministic policy priority
Teacher and specialist model opinions SHALL NOT override deterministic mastery gates or evidence-sufficiency rules.

### RQ-AGT-014 Failure handling
If a specialist fails, the action SHALL either fail safely or continue with an explicit limitation according to the action's safety requirements; it SHALL never silently pretend the agent participated successfully.

### RQ-AGT-015 State mutation
Specialist agents SHALL NOT independently write shared progression/exam state; application services commit validated decisions.

### RQ-AGT-016 Provider independence
Logical agents MAY share one configured LLM provider/model; role boundaries, schemas, and invocation logs SHALL remain distinct.

### RQ-AGT-017 Adaptive practice
Teacher/Trainer SHALL use stage, gaps, recurring errors, and prior evidence to adapt practice and explain why it was selected.

### RQ-AGT-018 Agent audit
The system SHALL record each agent invocation's action, status, timestamps, validation state, and relevant evidence references.

### RQ-AGT-019 No arbitrary tool authority
Subagents SHALL NOT execute arbitrary shell commands or autonomously modify student source files.

### RQ-AGT-020 Role conflict resolution
Teacher SHALL prioritize deterministic evidence and configured policy over conflicting agent opinions and record material conflicts.
