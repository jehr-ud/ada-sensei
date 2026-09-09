# Design

## Components

```text
Question
   ↓
QuestionClassifier        # conceptual | implementation | debugging | architecture | tooling | testing
   ↓
ContextBuilder
   ├── Conversation        # SessionContext.conversation (bounded)
   ├── Student Profile     # HistoryStore
   ├── Project Files       # ProjectInspector (read-only)
   └── Knowledge           # taxonomy + curated knowledge (005-examples)
   ↓
TutorAgent                 # LLM (structured/chat pipeline)
   ↓
Answer
```

## Question Types

- conceptual;
- implementation;
- debugging (requires project inspection);
- architecture;
- tooling;
- testing.

## Progressive Assistance

`/ask` shares the session `assistance_level`:

- `/hint`   → next hint for the current answer (regenerated with the hint).
- `/more`   → advance one `AssistanceLevel`:
  guiding_question → hint → conceptual_explanation → code_fragment → solution.
- `/solution` → `AssistanceLevel.solution`.

The previous answer text is kept in `SessionContext.conversation` so escalation
regenerates in context, not from scratch. No re-classification is needed on
escalation.

## Evidence and Citations

`ContextBuilder` attaches file excerpts with `file:line` provenance to the
prompt. `TutorAgent` is instructed to cite provenance for project-specific
claims and to emit an explicit "insufficient evidence" statement otherwise
(RQ-ASK-008).

The student profile is loaded for `SessionContext.student_id` only; identity is
never inferred from the question text (ADR-015).

## Safety

The action only reads through `ProjectInspector`; write tools are not
instantiated in the Ask action (RQ-ASK-007).