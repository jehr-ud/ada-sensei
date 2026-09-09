# Requirements

## RQ-PRA-001

The system SHALL generate an Android programming exercise when `/practice` is invoked.

## RQ-PRA-002

Each exercise SHALL specify a learning objective.

## RQ-PRA-003

Each exercise SHALL specify a difficulty level from {beginner, intermediate, advanced}, validated by the CLI.

## RQ-PRA-004

Each exercise SHALL contain explicit functional requirements.

## RQ-PRA-005

The system SHALL identify the main Android/Kotlin topics involved.

## RQ-PRA-006

The system SHALL consider available student history when generating an exercise (adaptive mode).

## RQ-PRA-007

The system SHALL avoid providing the complete solution by default.

## RQ-PRA-008

The system SHALL support progressive hints.

## RQ-PRA-009

A generated exercise SHALL contain enough information for the student to implement it independently.

## RQ-PRA-010

The exercise SHALL be representable as structured data so it can later be evaluated against the same requirements.

## RQ-PRA-011 Topic input

The system SHALL accept an explicit `--topic`; when omitted, it SHALL select a topic from student history or a stated default.

## RQ-PRA-012 Difficulty input

The system SHALL accept `--difficulty` and validate it against {beginner, intermediate, advanced}.

## RQ-PRA-013 Optional objective

The system SHALL accept an optional `--objective` that overrides the generated objective.

## RQ-PRA-014 Adaptive mode

The system SHALL default to adaptive generation when student history exists; `--no-adaptive` SHALL disable it.

## RQ-PRA-015 Exercise persistence

The generated exercise SHALL be persisted and retrievable by its stable `exercise://<uuid>` id (RQ-FND-012).

## RQ-PRA-016 Stable requirement ids

Each functional requirement SHALL carry a stable `req://<uuid>` id and the exercise's `evaluation_criteria` SHALL reference those ids (RQ-FND-010, ADR-009).

## RQ-PRA-017 Progressive assistance

The action SHALL honor `/hint`, `/more`, and `/solution`, maintaining the
assistance level in the session (RQ-FND-016, ADR-010).

## RQ-PRA-018 Student project safety

Practice SHALL never modify the student's project directory.

## RQ-PRA-019 Attempt record

Practice SHALL create and persist an `Attempt` (`attempt://<uuid>`) binding the
session `student_id`, the `project_id`, and the generated `exercise_id`, and
SHALL set it as the session attempt (RQ-FND-022). Student identity SHALL be read
from the session only, never inferred (ADR-015).

---

## Traceability

| Requirement | Component | Test |
|---|---|---|
| RQ-PRA-001 | `ada_sensei.actions.practice.PracticeAction` | `tests/actions/practice/test_practice.py::test_generates_exercise` |
| RQ-PRA-002 | `ExerciseSpecification` → prompt | `tests/actions/practice/test_practice.py::test_has_objective` |
| RQ-PRA-003 | `PracticeInput` validator + CLI | `tests/actions/practice/test_practice.py::test_difficulty_validated` |
| RQ-PRA-004 | `ExerciseSpecification` → prompt | `tests/actions/practice/test_practice.py::test_has_requirements` |
| RQ-PRA-005 | `ExerciseSpecification` → prompt | `tests/actions/practice/test_practice.py::test_has_topics` |
| RQ-PRA-006 | `StudentContext` | `tests/actions/practice/test_practice.py::test_adaptive_history` |
| RQ-PRA-007 | prompt template | `tests/actions/practice/test_practice.py::test_no_solution_default` |
| RQ-PRA-008 | `Exercise.hints` | `tests/actions/practice/test_practice.py::test_progressive_hints` |
| RQ-PRA-009 | `ExerciseSpecification` → prompt | `tests/actions/practice/test_practice.py::test_self_contained` |
| RQ-PRA-010 | `Exercise` validation | `tests/actions/practice/test_practice.py::test_structured_roundtrip` |
| RQ-PRA-011 | `PracticeInput` + CLI | `tests/actions/practice/test_practice.py::test_topic_from_history_or_default` |
| RQ-PRA-012 | `PracticeInput` validator | `tests/actions/practice/test_practice.py::test_invalid_difficulty_rejected` |
| RQ-PRA-013 | `PracticeInput.objective` | `tests/actions/practice/test_practice.py::test_objective_override` |
| RQ-PRA-014 | `PracticeAction` | `tests/actions/practice/test_practice.py::test_adaptive_default_on` |
| RQ-PRA-015 | `ExerciseStore` | `tests/actions/practice/test_practice.py::test_exercise_persisted_and_loaded` |
| RQ-PRA-016 | `ExerciseStore` / Criterion | `tests/actions/practice/test_practice.py::test_requirement_ids_stable` |
| RQ-PRA-017 | action + `SessionContext` | `tests/actions/practice/test_practice.py::test_assistance_level_advance` |
| RQ-PRA-018 | `PracticeAction` | `tests/actions/practice/test_practice.py::test_no_project_writes` |
| RQ-PRA-019 | `AttemptStore` + `SessionContext` | `tests/actions/practice/test_practice.py::test_attempt_created_and_bound` |