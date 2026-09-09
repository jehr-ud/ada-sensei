# Ask Action Specification

## Objective

Allow students and instructors to ask questions about Android development and
receive contextual, pedagogically appropriate explanations.

## Core Behavior

`/ask` SHALL answer questions using:

- the current conversation (bounded; `SessionContext.conversation`);
- relevant project files when available (read-only inspection);
- Android knowledge;
- student context when available (`HistoryStore`).

## Question Classification

The system SHALL distinguish at least: conceptual, implementation, debugging,
architecture, tooling, testing (RQ-ASK-004).

## Pedagogical Behavior

The system SHALL prefer explanations that promote understanding. For debugging
questions, inspect relevant project files before making strong claims, and cite
the relevant file or evidence (RQ-ASK-005).

Progressive assistance uses the shared `AssistanceLevel` scale
(001-foundation, ADR-010). In Ask, `/more` escalates from a guiding question to
a detailed solution; `/hint` reveals the next hint; `/solution` jumps to the
detailed solution.

## Evidence

- Claims about the student's project SHOULD reference `file[:line]` where known.
- When evidence is insufficient, the system SHALL state uncertainty explicitly
  (RQ-ASK-008).

## Safety

Ask SHALL not modify the student's project (RQ-ASK-007); context building uses
`ProjectInspector` which is read-only (RQ-FND-018).

## Example

```text
/ask Why doesn't my LazyColumn update after adding an item?

The agent inspects state handling (MainViewModel.kt:24) with evidence and
explains the cause before offering the fix.
```