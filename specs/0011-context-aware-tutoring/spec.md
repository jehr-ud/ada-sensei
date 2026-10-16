# Spec 0011 — Context-Aware Tutoring and Action Guidance

## 1. Purpose

ADA Sensei SHALL behave as an autonomous educational tutor, not merely a command executor. For each supported user action, the system SHALL explain briefly what the action does and what the student should do next. Responses SHALL be adapted to the student's current learning stage, selected action, available evidence, and selected locale.

After substantive educational interactions, ADA Sensei SHOULD recommend one useful next action when it can justify the recommendation from available context. Recommendations are optional and SHALL NOT execute automatically or independently advance the student.

## 2. Scope

This specification covers the GUI/TUI action selector, command entry points, action execution feedback, context-aware tutoring responses, and optional next-action recommendations for supported actions, including where implemented:

- Ask.
- Practice.
- Examples.
- Evaluate project.
- Start exam.
- Finish exam.
- View learning plan.
- Diagnostic.
- Change language.
- Help.
- Other actions present in the actual action registry.

The implementation MUST inspect the real action registry and include all supported student-facing actions. It SHALL NOT invent unsupported actions.

## 3. Action guidance in the selector

### 3.1 Guidance for every action

When an action is highlighted, focused, or selected in the GUI/TUI action selector, ADA Sensei SHALL show a short localized description of:
- What the action does.
- What the student should provide or do.
- What will happen after activation, when relevant.

The description SHOULD be one or two short sentences and should fit the existing interface.

Example guidance:

- **Ask:** “Ask a question about your current topic. Type your question after selecting this action.”
- **Practice:** “Work on a short exercise for your current learning stage.”
- **Examples:** “Request a code example related to the topic you are learning.”
- **Evaluate project:** “Analyze your current project against the requirements and available evidence.”
- **Start exam:** “Begin an exam if an exam definition is available. Follow the instructions shown next.”
- **Finish exam:** “Submit the active exam for evaluation. Make sure your work is saved first.”
- **View learning plan:** “See your current stage, objectives, and suggested next activities.”
- **Diagnostic:** “Check the available project or configuration diagnostics.”
- **Change language:** “Choose Español or English. The interface will update, and your learning progress will be preserved.”
- **Help:** “Show available actions and how to use ADA Sensei.”

These examples are guidance, not a hardcoded complete action list. The actual selector MUST use action metadata from the existing action registry or a centralized equivalent.

### 3.2 Discoverability and interaction states

The interface SHALL make it clear how to activate an action (for example, Enter to run, arrow keys to navigate, or the corresponding GUI control). It SHALL not rely solely on an undocumented keyboard shortcut.

When an action is selected, the interface SHALL either:
- Execute the action and show the next required input or result; or
- Show a clear instruction explaining what the student must do next.

The interface SHALL NOT leave the student at an unexplained blank prompt or silently do nothing.

For actions requiring parameters or additional input, show a localized prompt and, when useful, an example.

## 4. Context-aware responses

Before responding, the system SHOULD assemble relevant available context:
- Current stage and stable stage ID.
- Current learning objective.
- Selected action and validated parameters.
- Locale (`es-CO` or `en-US`).
- Relevant recent interaction result.
- Available assessment results and evidence.
- Outstanding requirements or prerequisites.
- Current project or exam context when applicable.
- Recent recommendations and their outcomes when available.

The system SHALL distinguish missing information from negative assessment results. It SHALL NOT invent student preferences, history, mastery, evidence, or project facts.

Responses SHALL be adapted to the current stage and action. If essential context is unavailable, the system SHALL ask for clarification or provide a qualified response.

## 5. Recommendations after interactions

After a substantive educational interaction, TeacherAgent or the existing orchestrator SHALL determine whether a useful next action is appropriate.

When justified, present one primary recommendation containing:
- Stable supported action ID.
- Validated parameters, if required.
- Localized label.
- Brief rationale.
- Intended learning objective.
- Applicable prerequisites.

Recommendations SHALL be validated against the action registry and prerequisite rules. Unsupported actions SHALL NOT be presented as executable.

The student SHALL be able to accept, dismiss, ignore, or request an alternative where supported. A recommendation SHALL NOT execute until the student explicitly selects it. Dismissing or ignoring it SHALL NOT penalize mastery or progression.

If no useful recommendation can be justified, do not invent one. Summarize the outcome, ask a relevant follow-up, or invite the student to choose another action.

## 6. Change language behavior

Selecting `Change language` SHALL start an explicit language-selection flow. It SHALL NOT merely change the highlighted selector item or return to an unexplained prompt.

The flow SHALL:
1. Present the supported options `Español` and `English`.
2. Indicate how to select and confirm an option.
3. Persist the selected locale using the existing settings/profile mechanism.
4. Refresh visible interface labels, help, action descriptions, and status messages.
5. Confirm the selected language in that language.
6. Preserve learning stage, mastery, attempts, evidence, exam history, and evaluation records.

Supported locale identifiers are `es-CO` and `en-US`. Machine identifiers and program behavior SHALL remain language-independent.

## 7. Component responsibilities

- **Orchestrator / TeacherAgent:** routes actions, assembles context, presents results, and coordinates recommendations.
- **Planner:** selects suitable learning activities using the current stage, evidence, prerequisites, and configured progression policy.
- **Trainer:** explains concepts, generates examples/practice, and adapts educational responses.
- **Evaluator:** assesses configured criteria using actual evidence and returns structured results.
- **Action registry:** defines supported actions, stable IDs, localized labels/descriptions, parameter requirements, and handler references or routes.
- **Localization service:** provides labels, instructions, help, and fallback behavior.

Reuse equivalent existing components. Do not create duplicate agents or registries if the current implementation already provides them.

## 8. Recommendation priorities and progression safeguards

The Planner SHOULD prioritize:
1. Resolving a blocking error or missing prerequisite.
2. Addressing an evidenced learning difficulty.
3. Completing an outstanding requirement.
4. Reinforcing a concept through practice or explanation.
5. Checking comprehension when required.
6. Suggesting the next objective when justified.

A recommendation SHALL NOT change the official learning stage. Only the authorized progression component SHALL update stage state under the existing evidence-based policy. Activity completion, question count, elapsed time, or accepting a recommendation SHALL NOT independently establish mastery.

## 9. Localization and failures

All action descriptions, prompts, result messages, and recommendations SHALL support `es-CO` and `en-US`.

Missing translations SHALL use the existing deterministic fallback and diagnostics. Locale SHALL NOT alter scoring, rubric weights, criterion IDs, evidence interpretation, or progression.

Handle missing context, invalid configuration, unsupported actions, missing parameters, unavailable providers, invalid structured output, unmet prerequisites, and persistence failures. Never represent a failed action as successful. Follow the repository's existing retry limit, including no more than three total structured-output attempts where specified.

## 10. Acceptance criteria

1. Every supported student-facing action has a concise localized description in the selector.
2. The interface explains how to activate the highlighted action.
3. Selecting `Change language` leads to an explicit, usable language-selection flow.
4. Actions requiring further input show a clear localized prompt and optional example.
5. After an action executes, the student receives a result or clear next-step instruction.
6. Substantive interactions receive a justified next-action recommendation when useful.
7. Recommendations are valid, optional, and explicitly executed by the student.
8. Recommendations do not independently advance the official learning stage.
9. Responses and action guidance adapt to stage and locale.
10. Existing commands, progress records, and assessment behavior remain compatible.
11. Automated tests cover selector descriptions, action routing, language selection, recommendations, localization, and progression safeguards.
