# 0010 — Language Selection and Localization

## Status
Proposed specification. This spec is the source of truth for selecting and applying the user's language across ADA Sensei.

## Purpose
Allow each student to choose **Spanish** or **English** and keep all student-facing ADA Sensei interactions in the selected language, including onboarding, learning stages, agent responses, assessment feedback, and examination reports.

## Scope
- Supported locales: `es-CO` (Spanish) and `en-US` (English).
- First-run language selection before the welcome/onboarding flow.
- Persist the preference per local student profile.
- Allow changing language from settings and the welcome screen.
- Localize stage catalog, rubrics, progression feedback, CLI/TUI labels, agent prompts, and generated reports.
- Preserve stable machine identifiers and language-neutral enums.

Out of scope:
- Automatic translation of student source code, identifiers, or external project files.
- Adding other languages in this version.
- Using the LLM as the sole source of UI translations.

## User stories
1. As a new student, I can choose Spanish or English before starting.
2. As a returning student, ADA Sensei uses my saved language without asking again.
3. I can change language at any time without losing my stage, attempts, evidence, or exam history.
4. The welcome screen explains ADA Sensei's objective, learning stages, and the options to take a diagnostic or select a starting stage in the selected language.
5. The same stage, rubric, and progression policy can be rendered in either language without changing IDs or scoring rules.

## Requirements

### RQ-LNG-001 — Supported languages
The application SHALL support `es-CO` and `en-US`. The visible selector SHALL label them as `Español` and `English`.

### RQ-LNG-002 — First-run selection
If no language preference exists, the application SHALL display a language selection screen before the welcome flow. The student must explicitly choose a language to continue. A configurable default may be preselected, but it must not be silently treated as the user's choice.

### RQ-LNG-003 — Persistence
The selected locale SHALL be stored in the student profile/settings. Restarting ADA Sensei SHALL preserve the choice.

### RQ-LNG-004 — Change language
The student SHALL be able to change the locale from the welcome screen and settings. Changing locale SHALL NOT reset stage progress, mastery records, attempts, exam history, or evidence.

### RQ-LNG-005 — Localization coverage
All student-facing static text SHALL be available in both supported languages, including:
- welcome and onboarding;
- stage titles, objectives, descriptions, learning outcomes, concepts and activities;
- action selector, input hints, status messages, errors and confirmations;
- agent explanations, examples, practice prompts and feedback;
- evaluation criteria, rubric labels, progression outcomes and recommendations;
- exam prompts, reports and generated PDF labels.

### RQ-LNG-006 — Configuration files
The application SHALL load a locale-specific variant of `stages.json`, `stage-rubrics.json`, and `progression-policy.json`, or an equivalent schema that explicitly stores both translations. The active locale MUST be validated against the supported locale list.

### RQ-LNG-007 — Stable identifiers
Changing locale SHALL NOT change `stage_id`, rubric IDs, criterion IDs, challenge IDs, action names, evidence IDs, status enums, score values, weights, or progression thresholds.

### RQ-LNG-008 — Deterministic fallback
If a translation is missing, the localization resolver SHALL use the configured fallback locale (`en-US` by default for missing keys) and record a diagnostic. It SHALL NOT silently ask the LLM to invent a translation for critical rubric criteria or scoring rules.

### RQ-LNG-009 — Agent instructions
TeacherAgent SHALL pass the active locale to PlannerAgent, EvaluatorAgent, and TrainerAgent. All user-visible output from all agents SHALL use that locale. Machine-readable keys and enum values SHALL remain language-neutral.

### RQ-LNG-010 — Assessment consistency
Localization SHALL change labels and explanatory text only. It SHALL NOT change scoring algorithms, criterion weights, criticality, evidence requirements, or progression decisions.

### RQ-LNG-011 — User-authored content
The language of student prompts and source code SHALL be preserved. Agents may answer in the selected locale, unless the student explicitly requests another language for a specific answer.

### RQ-LNG-012 — Exams and reports
`exam-init` and `exam-finish` SHALL use the active locale for student-facing messages and reports. The locale used for an exam SHALL be recorded at exam start so the report is consistent even if the profile language later changes.

### RQ-LNG-013 — Accessibility and TUI
The language selector SHALL be keyboard accessible and usable in the CLI/TUI. It SHALL use a short explicit choice (`Español` / `English`) and not depend on device locale availability.

### RQ-LNG-014 — Tests
Automated tests SHALL verify:
- first-run selection is shown when no preference exists;
- saved locale is loaded on restart;
- locale can be changed without mutating learning data;
- all configured stage and rubric IDs remain identical across locales;
- score and progression decisions are identical for the same evidence in both locales;
- missing translation fallback is deterministic;
- exam reports use the locale captured at exam start.

## Design

### Locale values
Use BCP-47-style locale identifiers:
- `es-CO`
- `en-US`

Do not use translated strings as internal identifiers.

### Preference model
```json
{
  "locale": "es-CO",
  "locale_source": "student_selection",
  "updated_at": "ISO-8601 timestamp"
}
```
`locale_source` is metadata and SHALL be one of `student_selection`, `configured_default`, or `migration`.

### Resolution
1. Read the student's saved locale.
2. If absent, show the selection screen.
3. Validate the chosen locale against supported locales.
4. Load the corresponding configuration bundle.
5. Pass the locale through the TeacherAgent orchestration context.
6. Render all user-facing text in that locale.
7. Keep IDs, scoring, and decisions language-neutral.

### Configuration layout
```text
config/
  i18n/
    stages.es.json
    stages.en.json
    stage-rubrics.es.json
    stage-rubrics.en.json
    progression-policy.es.json
    progression-policy.en.json
```
The provided files may use the equivalent naming convention `stages.es.json`, `stages.en.json`, etc. They retain the same structural schema and IDs across locales.

### Welcome flow
1. If locale is missing, show language selection.
2. Show the ADA Sensei objective in the selected language.
3. Show all learning stages in the selected language.
4. Offer two paths:
   - `Take initial diagnostic` / `Realizar diagnóstico inicial`
   - `Choose a starting stage` / `Elegir una etapa inicial`
5. Selecting a stage does not mark skipped stages as mastered.

### Agent contract
Every agent invocation receives:
```json
{
  "locale": "es-CO",
  "fallback_locale": "en-US"
}
```
Agents must return user-facing text in the requested locale while retaining canonical machine fields such as `READY`, `NOT_READY`, and criterion IDs.

## Tasks
- T001: Add locale preference model and persistence.
- T002: Add first-run language selector to CLI/TUI.
- T003: Add settings/welcome language switching.
- T004: Add locale configuration loader and schema validation.
- T005: Localize welcome and stage-selection flow.
- T006: Pass locale through TeacherAgent and all subagent contracts.
- T007: Localize action prompts, errors, status labels, and help.
- T008: Localize rubric explanations and progression feedback without changing scoring.
- T009: Capture locale at `exam-init` and use it in `exam-finish` report.
- T010: Add parity tests for IDs, weights, gates, and decisions.
- T011: Add missing-translation diagnostics and fallback tests.
- T012: Document how to add another locale in the future.

## Acceptance criteria
- A new student must choose Spanish or English before seeing onboarding.
- A returning student sees the saved language.
- The student can switch language without losing progress.
- Stage/rubric/policy IDs and scoring behavior are identical across locales.
- Teacher and all three subagents use the selected language for user-facing content.
- Exam reports use the language selected when the exam began.
