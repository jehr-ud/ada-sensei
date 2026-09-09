# Design

## Components

```text
/examples <topic>
    ↓
TopicResolver             # normalizes against knowledge/ taxonomy
    ↓
KnowledgeRetrieval        # curated knowledge/ entries
    ↓
ExamplePrompt             # JSON Schema for ExampleResult
    ↓
LLMClient                 # structured pipeline (001-foundation)
    ↓
ExampleResult
```

## Example Model

```text
ExampleResult
- id: example://<uuid>            # only when persisted/curated
- concept: str                    # RQ-EX-002
- level: basic | intermediate | advanced
- body: str                       # code + explanation why it works (RQ-EX-003)
- common_mistake?: {incorrect_code, explanation}   # RQ-EX-005/006
- teaching_questions: [str]       # RQ-EX-007
- derived_exercise?: exercise://<id>   # when an exercise is generated
- source: curated | generated
```

## Behavior

- `TopicResolver` maps the requested topic to `knowledge/`; unknown topics
  produce a clear error listing known topics.
- Curated entries are returned directly when available; otherwise the LLM
  generates under the schema above.
- Intentionally incorrect examples SHALL be flagged (`common_mistake`) so they
  can never be mistaken for correct code (RQ-EX-006).
- `--teacher` flag (future) only changes the output profile: adds discussion
  points without a separate agent (RQ-EX-011).

## Instructor Mode

Future-proofed as a rendering/prompt profile, not as a distinct action.