# Agent Orchestration Specification

## Objective

Every student-facing action is coordinated by one principal autonomous agent,
`TeacherAgent`, with exactly three specialist subagents: `PlannerAgent`,
`EvaluatorAgent`, and `TrainerAgent`. The Teacher's product-level objective is to
help the student learn to design, build, explain, test, and improve Android apps.

## Agent responsibilities

### TeacherAgent — principal/orchestrator
- owns the interaction plan and final response;
- interprets intent and current session/stage context;
- invokes Planner, Evaluator, and Trainer for every student-facing action;
- selects/reuses existing action capabilities instead of reimplementing them;
- reconciles specialist outputs, resolves conflicts using policy/evidence, and
  decides the next pedagogical step;
- asks the student for confirmation before stage transition when applicable.

### PlannerAgent — progression and learning evidence
- tracks current stage, goals, prerequisites, and progress;
- records and organizes evidence for the current stage;
- determines whether mastery gates permit transition to the next stage;
- recommends remediation or the next stage/activity;
- never treats missing evidence as mastery and never scores solely from chat volume.

### EvaluatorAgent — diagnostics and assessment
- runs initial diagnostics and in-stage diagnostics;
- designs/coordinates stage exit assessments;
- evaluates Android project evidence through `006-evaluate`;
- coordinates formal exam assessment via `007-examine`;
- returns evidence references, criterion scores, confidence/limitations, and gaps;
- does not itself change the student's learning stage.

### TrainerAgent — teaching and practice
- explains the key concepts of the current stage;
- reuses `/ask` for doubts, `/examples` for examples, and `/practice` for challenges;
- adapts explanation, hints, examples, and practice difficulty to current gaps;
- follows the progressive-assistance policy and favors scaffolding over full answers;
- does not decide progression or invent assessment evidence.

## Mandatory invocation rule

Every student-facing action SHALL invoke all three specialist subagents once as
part of the action's orchestration cycle, in addition to TeacherAgent. A specialist
may return `not_applicable` for a subtask, but it must still return a typed result
with rationale. This rule is about participation, not requiring every specialist
to generate visible content or duplicate work. For example, during `/ask`, Trainer
answers, Planner checks the learning objective/progress implications, and Evaluator
identifies whether a diagnostic misconception should be recorded. During
`/exam-finish`, Evaluator assesses, Planner records evidence without advancing the
stage, and Trainer returns feedback/recommended study topics.

## Reuse of existing actions

The orchestration layer MUST call existing application action services, not shell
out to the CLI or recursively invoke slash commands:

- `/ask` → `AskAction`
- `/practice` → `PracticeAction`
- `/examples` → `ExamplesAction`
- `/evaluate` → `EvaluateAction` / reusable `EvaluationEngine`
- `/exam-init` → `ExamInitAction`
- `/exam-finish` → `ExamFinishAction`
- `/learn` → learning plan/current stage query
- `/diagnose` → `DiagnosticService` coordinated by EvaluatorAgent

The existing action contracts, safety checks, confirmation requirements, and
persistence remain authoritative. Agent orchestration wraps these actions rather
than duplicating their business logic.

## Intent flows

### First-run onboarding
1. Establish explicit student identity according to foundation policy.
2. Teacher shows goal and stage catalog.
3. Student chooses initial diagnostic or a starting stage.
4. Evaluator conducts diagnostic if selected.
5. Planner recommends stage/plan from diagnostic evidence and prerequisites.
6. Trainer explains what learning that stage means and offers the first activity.
7. Teacher persists the onboarding outcome and presents one response.

### Study: learn
1. Teacher reads current stage and learning goal.
2. All three specialists return typed outputs.
3. Trainer provides stage explanation, examples, and a short understanding check.
4. Planner logs the learning event and notes current stage evidence.
5. Evaluator flags misconceptions/diagnostic signals but does not mark mastery from exposure alone.

### Study: practice
1. Teacher asks Planner for current gaps and next useful objective.
2. Trainer generates/adapts a practice task via `PracticeAction`.
3. Evaluator defines observable success criteria and reviews returned evidence where appropriate.
4. Planner records attempt evidence and recommends practice or exit assessment.

### Study: ask/examples
Teacher routes to existing `AskAction` or `ExamplesAction`; Planner and Evaluator
still return relevant progress/diagnostic annotations. Trainer owns the instructional
content. A normal answer/example alone cannot mark a competency mastered.

### Study: mastery evaluation
1. Evaluator creates an exit challenge aligned to the current stage rubric.
2. Existing `EvaluationEngine` collects project/build/test/static analysis evidence.
3. Evaluator gathers a comprehension/transfer check.
4. Planner applies the configured `ProgressionPolicy` and stores the decision.
5. Teacher reports gate-by-gate outcome; if ready, asks/handles transition; if not,
   routes the student to targeted practice.

### Examine
`/exam-init` and `/exam-finish` may be requested at any stage. Teacher orchestrates
all three agents; Evaluator delegates to `007-examine`; Planner records the exam as
separate evidence and MUST NOT auto-advance the stage; Trainer gives post-exam
feedback consistent with exam policy. Exam ask/duration metrics are not automatically
used as mastery penalties.

## Agent input/output contracts

Each agent receives a minimized `AgentContext`: student/project ids, current intent,
current stage, relevant learning goals, recent history summary, active action request,
applicable evidence, assistance level, and policy/catalog versions. Apply the
foundation `ContextManager`; preserve identity, active task, and safety constraints.

Every subagent returns a schema-validated envelope:

- `agent_id`: `planner | evaluator | trainer`
- `status`: `ok | not_applicable | insufficient_context | failed`
- `summary`: concise, bounded text
- `structured_payload`: typed role-specific object
- `evidence_refs`: list of existing evidence ids (never fabricated)
- `uncertainties`: explicit unknowns/limitations
- `recommended_next_step`: optional action id + rationale

TeacherAgent also produces a typed `TeacherDecision` with selected action result,
progression decision reference if any, conflicts/limitations, and final response.
Agent outputs are data, not executable instructions. Do not allow subagents to
change system policy, call arbitrary shell commands, or write project files.

## Failure and conflict handling

- Each specialist uses the existing structured-output validation policy (maximum
  three total attempts per structured response).
- If a specialist fails, Teacher continues only when safe, marks the missing role
  output as unavailable, and discloses the limitation when it affects the answer.
- Planner cannot override deterministic policy gates; Evaluator cannot invent tool
  evidence; Trainer cannot change rubric scores; Teacher cannot silently override
  persisted policy decisions.
- On conflicting recommendations, deterministic evidence and configured policy
  outrank model opinion. The conflict is recorded and summarized where relevant.
- Do not launch parallel specialist calls if they would mutate the same record;
  specialist outputs should be gathered first and committed by the application layer.

## Persistence and observability

Persist `AgentInvocation`/`LearningEvent` records with action, agent, timestamps,
status, model/provider, context references, output validation status, and errors.
Avoid storing unnecessary full private conversation content; store references or
bounded summaries where possible. Specialist invocation failures are testable.

## Non-goals

This spec does not require four separate model instances or four different model
providers. Agents are role-bounded logical agents; implementation may share one
LLM provider/model while using separate prompts, schemas, contexts, and invocation
records. It does not permit arbitrary autonomous modification of student source.
