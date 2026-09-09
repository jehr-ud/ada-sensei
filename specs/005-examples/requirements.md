# Requirements

## RQ-EX-001

The system SHALL generate or retrieve an example for a requested Android concept.

## RQ-EX-002

The example SHALL identify the concept it demonstrates.

## RQ-EX-003

The example SHALL include an explanation of why the implementation works.

## RQ-EX-004

The system SHOULD support different complexity levels (basic | intermediate | advanced).

## RQ-EX-005

The system SHOULD be able to provide a deliberately incorrect example when requested for teaching purposes.

## RQ-EX-006

Incorrect examples SHALL clearly identify that they are intentionally incorrect.

## RQ-EX-007

The system SHOULD provide teaching questions that an instructor can ask students.

## RQ-EX-008

Examples SHALL be independent from the student's project unless project context is explicitly requested.

## RQ-EX-009 Exercise-derived example

The system MAY generate an exercise derived from a requested example, using the
practice exercise structure and persisting it through `ExerciseStore`
(RQ-PRA-015).

## RQ-EX-010 Topic taxonomy

The system SHALL validate requested topics against the `knowledge/` taxonomy and
report unknown topics clearly.

## RQ-EX-011 Instructor mode

The architecture SHALL support a future `--teacher` flag that only changes the
output profile (teaching questions, discussion points) without a separate agent.

## RQ-EX-012 Structured output

Examples SHALL be produced through the structured LLM pipeline; malformed output
SHALL fail cleanly (RQ-FND-008).

---

## Traceability

| Requirement | Component | Test |
|---|---|---|
| RQ-EX-001 | `ada_sensei.actions.examples.ExamplesAction` | `tests/actions/examples/test_examples.py::test_get_or_generate` |
| RQ-EX-002 | `ExampleResult.concept` | `tests/actions/examples/test_examples.py::test_identifies_concept` |
| RQ-EX-003 | `ExampleResult.body` | `tests/actions/examples/test_examples.py::test_explains_why` |
| RQ-EX-004 | `ExampleResult.level` | `tests/actions/examples/test_examples.py::test_levels` |
| RQ-EX-005 | `ExampleResult.common_mistake` | `tests/actions/examples/test_examples.py::test_intentional_mistake` |
| RQ-EX-006 | `ExampleResult.common_mistake` | `tests/actions/examples/test_examples.py::test_mistake_is_flagged` |
| RQ-EX-007 | `ExampleResult.teaching_questions` | `tests/actions/examples/test_examples.py::test_teaching_questions` |
| RQ-EX-008 | `ExamplesAction` | `tests/actions/examples/test_examples.py::test_no_project_touch` |
| RQ-EX-009 | `ExamplesAction` → `ExerciseStore` | `tests/actions/examples/test_examples.py::test_derived_exercise` |
| RQ-EX-010 | `TopicResolver` | `tests/actions/examples/test_topic_resolver.py::test_unknown_topic_error` |
| RQ-EX-011 | prompt profile | `tests/actions/examples/test_examples.py::test_teacher_profile` |
| RQ-EX-012 | structured pipeline | `tests/actions/examples/test_examples.py::test_malformed_fails_cleanly` |