# ADA Sensei — Learning and Agent Specs Update

This update extends the supplied specs with two specs:

- `008-learning-path`: seven-stage Android learning catalog, first-run onboarding, configurable JSON rubrics, and mastery-learning progression policy.
- `009-agent-orchestration`: TeacherAgent plus PlannerAgent, EvaluatorAgent, and TrainerAgent; mandatory typed participation for each student-facing action; reuse of existing actions.

Key design constraints preserved:
- existing action services remain the source of behavior; orchestration does not duplicate them;
- `006-evaluate` keeps its default rubric and exposes a reusable engine;
- formal exams (`007-examine`) remain separate from study-stage progression;
- evidence-first assessment, structured-output validation (max three attempts), explicit identity, XDG persistence, and no default instrumented Android tests remain in force;
- question count alone is not a mastery penalty;
- advancement requires all configured gates, including construction, analysis/design, and comprehension.

Suggested implementation order: `001-foundation` contracts → `008-learning-path` models/catalog/policy → `009-agent-orchestration` → integration updates/tests for `002-cli`, `006-evaluate`, and `007-examine`.
