# Final Review — F1–F6 Resolution

This package is based on the latest uploaded specification package. The six
review findings were resolved without reverting the newer requirements.

- F1: `Attempt` is a foundation domain model with explicit `AttemptStore`
  persistence and lifecycle status.
- F2: context management performs deterministic reduction first; optional LLM
  summarization occurs only afterward and is explicitly LLM-derived.
- F3: structured output allows at most 3 total attempts: 1 initial + 2 retries.
- F4: non-interactive `evaluate` aborts before Gradle execution unless explicit
  `--yes` confirmation is supplied.
- F5: exercise functional criteria are normalized subweights inside the fixed
  40% functional dimension; they do not create additional global score weight.
- F6: successful evaluation marks the attempt completed and appends its outcome
  to student history, with explicit persistence-failure reporting.

No application implementation code is included.
