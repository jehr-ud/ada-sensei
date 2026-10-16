# Learning Path and Mastery Learning Specification

## Objective

Define the learning journey, onboarding, stage-specific assessment criteria, and
mastery-based progression independently of any one subject. The first catalog is
Android development, defined in `android-learning-catalog.json`.

## Student intents

- **Study**: learn, practice, ask questions, view examples, and request an exit
  assessment to determine readiness for the next stage.
- **Examine**: start and finish a formal exam at any time through `/exam-init` and
  `/exam-finish`. This intent is independent from the current study stage.

A formal exam is not automatically a mastery assessment and never silently
advances the stage.

## First-run onboarding

After identity confirmation and before normal action input, if the student has no
learning profile, show the goal: “Learn to design, build, explain, test, and
improve Android applications—not merely copy generated code.” Show all seven
stages in catalog order. Ask whether the student wants (a) an initial diagnostic
or (b) to choose a starting stage. The student can explicitly skip diagnosis.
Store the chosen catalog version, stage, and diagnostic state.

## Default Android stages

1. Fundamentos de Kotlin
2. Estructura de un proyecto Android
3. Activities y ciclo de vida
4. Construcción de interfaces con Jetpack Compose
5. Estado y arquitectura básica
6. Clean Architecture y calidad de código
7. Proyectos propios

The catalog's prerequisites are a learning graph, not merely display text. Stage
4 requires Kotlin and project-structure prerequisites; stage 5 requires Compose
and Activities/lifecycle. Instructors may configure a starting stage, but the
system SHALL distinguish a chosen starting point from demonstrated mastery of
skipped stages.

## Assessment dimensions

Every stage mastery assessment SHALL evaluate all three dimensions:

1. **Construction**: the learner can implement a working solution and provide
   observable evidence (source inspection, build/run where feasible, tests, or a
   working artifact).
2. **Analysis and design**: the learner can decompose the problem, justify
   choices, identify trade-offs, and design a solution before or during coding.
3. **Comprehension**: the learner can explain code/data flow and answer a transfer
   question, predict behavior, debug, or modify a requirement.

The stage-specific criteria are versioned in `stage-rubrics.json`. The generic
mastery engine consumes rubric JSON and does not hard-code Kotlin/Android concepts.

## Mastery loop

```text
TEACH -> PRACTICE -> EXIT CHALLENGE -> COLLECT EVIDENCE
  ^                                  |
  |                                  v
REMEDIATION <- NOT READY <- APPLY MASTERY POLICY -> READY -> NEXT STAGE
```

Completion, time spent, number of questions, or self-report alone SHALL NOT
establish mastery. Every attempt includes a practical challenge, evidence, and a
comprehension check. Reassessment uses an equivalent but not identical challenge.

## Default decision policy

The policy in `progression-policy.json` is a configurable starting point:

- score scale 0–4 for each criterion;
- weighted overall score >= 3.0/4;
- each of the three dimension scores >= 2.5/4;
- each critical criterion >= 2.0/4;
- evidence required for every dimension;
- exit challenge and comprehension check required.

All gates must pass. If a dimension has insufficient evidence, decision is
`NOT_READY` with reason `INSUFFICIENT_EVIDENCE`; it is not treated as a zero score
or as mastery. A high total score cannot compensate for a critical competency
below its threshold.

These are initial policy values, not empirically calibrated cut-offs. Store the
policy version and expose the reason for every decision. Instructor overrides
must be explicit and auditable.

## Initial diagnostic

The diagnostic is a baseline, not a pass/fail exam. EvaluatorAgent identifies
strengths, gaps, and evidence confidence for the catalog competencies. PlannerAgent
uses it to recommend a starting stage and a personalized learning plan. A student
may choose another stage; the UI must disclose unmet prerequisites and must not
record skipped stages as mastered.

## Adaptive practice

TeacherAgent uses the latest mastery evidence, recurring errors, current goal,
and assistance history to select the next activity. TrainerAgent may generate
explanations, examples, hints, and practice tasks. The student should receive a
short explanation of why a practice task is recommended. Repeated weakness should
cause a smaller prerequisite exercise or alternative explanation, not simply a
harder challenge.

## Persistence

Persist `LearningProfile`, `LearningPlan`, `LearningEvent`, `MasteryAssessment`,
and `ProgressionDecision` under ADA Sensei's data directory. Keep them separate
from `ExamAttempt` and `EvaluationResult`. Every result stores catalog, rubric,
policy, stage, challenge, and evidence references. Never write learning state into
the student's Android project.

## Non-goals

This specification does not define a cloud LMS, automatic identity verification,
or automatic mastery inference from chat volume. It does not require all seven
stages to be completed linearly if an instructor configures a different graph.
