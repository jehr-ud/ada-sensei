# Tasks — Agent Orchestration

## Phase 1 — Contracts
- [ ] Define typed input/output schemas for TeacherDecision and each specialist.
- [ ] Add AgentInvocation persistence/observability.
- [ ] Add role prompts and context builders with bounded context.

## Phase 2 — Orchestrator
- [ ] Implement TeacherOrchestrator as the single student-facing entry point.
- [ ] Invoke Planner, Evaluator, Trainer exactly once per action cycle.
- [ ] Reuse existing action services without CLI recursion or duplicate side effects.
- [ ] Add failure/conflict handling and structured output validation.

## Phase 3 — Integrate actions
- [ ] Route ask, practice, examples, evaluate, exam-init, and exam-finish through Teacher.
- [ ] Add learn and diagnose intents.
- [ ] Preserve evaluate confirmation and exam lifecycle constraints.

## Phase 4 — Learning integration
- [ ] Connect PlannerAgent to `008-learning-path` and its deterministic progression policy.
- [ ] Connect EvaluatorAgent to diagnostics, EvaluationEngine, and exam workflow.
- [ ] Connect TrainerAgent to existing ask/practice/examples action services.

## Phase 5 — Tests
- [ ] Test every action invokes all three specialists exactly once.
- [ ] Test a failed specialist is never reported as successful participation.
- [ ] Test no duplicate Gradle/exam side effects.
- [ ] Test deterministic mastery policy cannot be overridden by LLM output.
- [ ] Test exam completion never auto-promotes a student.
- [ ] Test role outputs are schema-validated and evidence refs exist.
