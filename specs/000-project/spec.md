# ADA Sensei — Project Specification

## 1. Purpose

ADA Sensei (Adaptive Development Assistant) is an AI-powered educational coding agent initially focused on Android development.

The system is intended to support both students and instructors through guided practice, contextual questions and answers, project evaluation, and teaching examples.

## 2. Initial Domain

The first domain is Android application development, with emphasis on:

- Kotlin
- Jetpack Compose
- Android architecture
- Android APIs
- Gradle
- Testing

## 3. Core Principle

ADA Sensei SHALL behave as a tutor rather than only as a code generator.

The system SHOULD favor guidance, explanation, hints, evidence-based feedback, and progressive assistance over immediately providing complete solutions.

## 4. Primary Actions

The initial product SHALL provide:

- `/practice`
- `/ask`
- `/examples`
- `/evaluate`

## 5. Spec-Driven Development

Every significant feature SHALL be represented by a specification containing:

- `spec.md`
- `requirements.md`
- `design.md`
- `tasks.md`

Requirements SHALL be testable and implementation SHALL be traceable to requirements.

### Spec Numbering and Dependency Order

Specs are numbered so that a lower number has no dependency on a higher number:

```text
000-project       purpose, scope, architecture decisions
001-foundation    shared infrastructure (config, LLM, models, persistence, tools)
002-cli           CLI, routing, interactive shell, progressive-assistance commands
003-practice      exercise generation and persistence
004-ask           contextual Q&A
005-examples      teachable examples
006-evaluate      evidence-based evaluation
```

`001-foundation` owns all cross-cutting concerns (ADR-006). Action specifications
SHALL reference foundation models and services instead of redefining them.

## 6. Initial Constraints

The MVP SHALL:

- run as a CLI;
- support an OpenAI-compatible/local LLM client abstraction;
- support Ollama as the first local provider;
- operate on a selected Android project/workspace;
- use deterministic tools for project inspection and execution;
- keep the LLM replaceable.

## 7. Out of Scope for MVP

- Training a foundation model from scratch.
- Full autonomous modification of student projects.
- Cloud multi-user platform.
- Mobile application UI.
- Automated grading without evidence.
- Full Android emulator orchestration (unit tests are collected by default;
  instrumented tests are reserved for a future explicit `--instrumented` option,
  and the system does not drive an emulator).
