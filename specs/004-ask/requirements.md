# Requirements

## RQ-ASK-001

The system SHALL accept natural-language questions.

## RQ-ASK-002

The system SHALL answer questions related to the configured Android domain.

## RQ-ASK-003

When a project is active, the system SHALL be able to inspect relevant project files before diagnosing project-specific issues.

## RQ-ASK-004

The system SHALL distinguish between general conceptual questions and project-specific debugging questions.

## RQ-ASK-005

For project-specific claims, the agent SHOULD cite the relevant file or evidence in its response.

## RQ-ASK-006

The system SHALL support progressive assistance.

## RQ-ASK-007

The system SHALL not modify the student's project merely because a question was asked.

## RQ-ASK-008

The system SHALL clearly state uncertainty when available evidence is insufficient.

## RQ-ASK-009 Conversation context

The system SHALL maintain the bounded conversation in the session and use it to
answer follow-up questions and to escalate assistance (`/more`) in-context
(RQ-FND-015, ADR-010).

## RQ-ASK-010 Student profile reuse

When a student profile exists, the system SHALL load it through `HistoryStore`
and provide it as context (RQ-FND-011).

## RQ-ASK-011 Escalation commands

`/hint`, `/more`, and `/solution` SHALL advance the shared assistance level for
the current answer without re-classifying the question.

---

## Traceability

| Requirement | Component | Test |
|---|---|---|
| RQ-ASK-001 | `ada_sensei.actions.ask.AskAction` | `tests/actions/ask/test_ask.py::test_accepts_question` |
| RQ-ASK-002 | `TutorAgent` → prompt | `tests/actions/ask/test_ask.py::test_android_domain` |
| RQ-ASK-003 | `ContextBuilder` + `ProjectInspector` | `tests/actions/ask/test_ask.py::test_inspects_project` |
| RQ-ASK-004 | `QuestionClassifier` | `tests/actions/ask/test_ask.py::test_classification` |
| RQ-ASK-005 | `TutorAgent` | `tests/actions/ask/test_ask.py::test_cites_evidence` |
| RQ-ASK-006 | `AssistanceLevel` (session) | `tests/actions/ask/test_ask.py::test_progressive_levels` |
| RQ-ASK-007 | `AskAction` (no write tools) | `tests/actions/ask/test_ask.py::test_no_project_writes` |
| RQ-ASK-008 | `TutorAgent` | `tests/actions/ask/test_ask.py::test_uncertainty_stated` |
| RQ-ASK-009 | `SessionContext.conversation` | `tests/actions/ask/test_ask.py::test_follow_up_in_context` |
| RQ-ASK-010 | `ContextBuilder` + `HistoryStore` | `tests/actions/ask/test_ask.py::test_uses_student_profile` |
| RQ-ASK-011 | `AskAction` + session | `tests/actions/ask/test_ask.py::test_escalation_without_reclassify` |