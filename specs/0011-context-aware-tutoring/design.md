# Spec 0011 — Design

## Design principles
- Guide the student before, during, and after action execution.
- Reuse the existing action registry and orchestration.
- Keep user-interface code separate from business logic.
- Make recommendations optional and evidence-grounded.
- Keep language presentation independent of machine IDs and scoring.

## Logical flow
```text
Action selector
  -> Focused action metadata (localized label + description + activation hint)
  -> Student activates action
  -> Action handler / TeacherAgent
  -> Context assembly (stage, objective, locale, relevant evidence)
  -> Appropriate workflow (Planner / Trainer / Evaluator as needed)
  -> Result or explicit next-input prompt
  -> Recommendation decision
  -> Validate action ID, parameters, prerequisites
  -> Localized result + optional recommendation
  -> Student explicitly selects recommendation
  -> Existing action workflow
```

## Action metadata
Reuse an existing registry. If one does not exist, define a centralized action definition containing stable action ID, localized label/description, activation hint, required parameters, availability/prerequisites, and handler reference. Avoid separate hardcoded lists in GUI, CLI, and TUI.

## Change language interaction
The action handler opens a clear choice of `Español` and `English`, persists the locale, refreshes labels/descriptions/status, and confirms the selection. The operation changes presentation only and must not mutate learning records.

## Context and recommendation
Reuse existing context/result models or define typed models. Missing information remains unknown. Recommendations use stable action IDs and validated parameters, never localized labels as executable values. The student must explicitly select a recommendation before it runs.

## Testing
Use fakes for LLM providers, handlers, and progress repositories. Test selector metadata coverage, action routing, parameter prompts, language switching and persistence, context propagation, recommendation validation, no automatic execution, and no progression mutation.
