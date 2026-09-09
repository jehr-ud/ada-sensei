# Tasks

- [ ] Define `PracticeInput` model with topic/difficulty/objective/adaptive validation.
- [ ] Define `Exercise`, `Requirement`, and `Criterion` models (foundation `models.py`).
- [ ] Implement `PracticeAction`.
- [ ] Implement student-context loading from `HistoryStore`.
- [ ] Implement default topic/difficulty resolution (history-aware + fallbacks).
- [ ] Create practice prompt template (with JSON Schema).
- [ ] Wire structured LLM response validation (foundation pipeline).
- [ ] Wire `ExerciseStore` persistence and `SessionContext.current_exercise_id`.
- [ ] Implement `AttemptStore` linkage (student_id + project_id + exercise_id → `attempt://`).
- [ ] Implement progressive assistance (`/hint`, `/more`, `/solution`) integration.
- [ ] Add unit tests (input validation, adaptive behavior, persistence, ids).
- [ ] Add integration tests with a fake LLM provider + sample exercises.