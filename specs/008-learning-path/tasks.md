# Tasks — Learning Path and Mastery

## Phase 1 — Contracts and validation
- [ ] Define versioned Pydantic models for catalog, stage, rubric, policy, mastery assessment, and progression decision.
- [ ] Add JSON Schema validation and reject duplicate ids, missing references, cycles, invalid weights, and invalid thresholds.
- [ ] Add fixtures for Android catalog, stage rubrics, and policy.

## Phase 2 — Persistence
- [ ] Add stores for learning profile, plan, learning events, mastery assessment, and progression decision.
- [ ] Add atomic persistence, migration/version checks, and round-trip tests.

## Phase 3 — Onboarding and diagnostic
- [ ] Add first-run welcome with goal and seven stages.
- [ ] Add diagnostic path and starting-stage selection path.
- [ ] Persist selected stage without marking skipped stages mastered.

## Phase 4 — Mastery evaluation
- [ ] Integrate with `006-evaluate` reusable engine using caller-supplied rubric.
- [ ] Add structured comprehension/transfer challenge.
- [ ] Implement deterministic scoring and all-gates progression policy.
- [ ] Test insufficient evidence, critical-gate failure, and boundary thresholds.

## Phase 5 — Adaptive practice
- [ ] Recommend practice from criterion gaps and recurring errors.
- [ ] Generate equivalent non-identical reassessment challenges.
- [ ] Explain recommendations and retain prior evidence.

## Phase 6 — Integration
- [ ] Route learn/diagnose/evaluate intents through `TeacherAgent` in `009-agent-orchestration`.
- [ ] Verify exam results remain separate from progression decisions.
- [ ] Add end-to-end tests for all seven stages and a sample non-Android catalog.
