# Design — Agent Orchestration

## Application flow

```text
CLI/TUI CommandRouter
        ↓
TeacherAgent (intent + orchestration)
   ├── PlannerAgent
   ├── EvaluatorAgent
   ├── TrainerAgent
   └── Existing Action Services (ask/practice/examples/evaluate/exam)
        ↓
Validated Agent Outputs + Action Result
        ↓
TeacherDecision
        ↓
Application services persist events/decisions
        ↓
TUI/CLI presenter
```

## Suggested package layout

```text
ada_sensei/agents/
  contracts.py
  teacher.py
  planner.py
  evaluator.py
  trainer.py
  orchestrator.py
  prompts/
  schemas/
ada_sensei/learning/
  catalog.py
  diagnostic.py
  mastery.py
  progression.py
  stores.py
```

The names are a proposed organization, not permission to duplicate existing
modules. Adapt to the repository's actual layout while preserving these boundaries.

## Per-action invocation contract

`TeacherOrchestrator.handle(command, session_context)`:
1. Resolve student, project, intent, stage, and action service.
2. Build bounded role-specific contexts.
3. Invoke PlannerAgent, EvaluatorAgent, and TrainerAgent once each; do not ask them
   to all produce the same user-facing answer.
4. Execute/reuse the relevant existing action service once, subject to safety and
   confirmation rules.
5. Validate all role outputs and action result.
6. Construct TeacherDecision, apply deterministic policy, and persist events in a
   single application-layer commit where practical.
7. Render final response through CLI/TUI presenter.

For actions that have side effects, preserve existing ordering/confirmation rules.
The mandatory three-agent participation must not cause duplicate Gradle runs,
duplicate exam starts/finishes, or repeated writes. Agent invocations may happen
before/after action execution according to their information needs, but the actual
action service executes once.

## Action-to-agent contribution matrix

| Intent/action | Planner | Evaluator | Trainer |
|---|---|---|---|
| onboarding | recommend stage/plan | initial diagnostic or N/A | explain goal/stages |
| learn | record learning event | identify misconceptions / N/A | explain current-stage concepts |
| practice | choose gap-based objective | define/check success criteria | create adaptive challenge |
| ask | connect question to goal | tag diagnostic signal / N/A | answer progressively |
| examples | identify competency target | note likely check / N/A | provide stage-appropriate examples |
| evaluate mastery | apply gates and persist decision | design and assess exit challenge | prepare instructions and feedback |
| exam-init | record exam event only | validate/initialize exam | explain rules and permitted help |
| exam-finish | record separate evidence, no promotion | assess project and generate report | explain outcomes and next learning targets |

## Avoiding agent theatre

The implementation must not merely print three agent names. Each invocation must
produce a typed result used by TeacherDecision or explicitly marked `not_applicable`
with rationale. Tests assert one invocation record per specialist for each
student-facing action and assert the final response is grounded in action/evidence.

## Security and project boundary

Agents receive only the project excerpts and evidence needed for their role. They
cannot call shell or filesystem tools directly. Deterministic tools are exposed via
existing application services with explicit allowlists. Student project writes
remain prohibited except separately specified, user-confirmed generated files.
