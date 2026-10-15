"""RQ-EXM-026/027: exam results persist, reach history, failures surface."""

from __future__ import annotations

from ada_sensei.actions.examine import (
    ExamFinishInput,
    ExamineAction,
    ExamStartInput,
)
from ada_sensei.exams.models import (
    ExamResult,
    ExamStatus,
    ScoreCalculation,
)
from ada_sensei.storage.history import HistoryStore
from ada_sensei.storage.results import ResultStore
from exams_helpers import (
    STATEMENT_MARKDOWN,
    OkRunner,
    make_attempt,
    make_context,
    make_evidence,
)


def _result() -> ExamResult:
    attempt = make_attempt(status=ExamStatus.completed)
    evidence = make_evidence()
    return ExamResult(
        id="result://r1",
        student_id=attempt.student_id,
        project_id=attempt.project_id,
        exam_id=attempt.exam_id,
        exam_attempt_id=attempt.exam_attempt_id,
        attempt_id=attempt.attempt_id,
        exam_title="Test exam",
        evidence=list(evidence.evidence),
        score_calculation=ScoreCalculation(
            rubric_id="exam-default",
            rubric_version="v1",
            raw_score_50=44,
            max_raw_score=50,
            suggested_grade=4.5,
            min_grade=1.0,
            max_grade=5.0,
        ),
        raw_score_50=44,
        suggested_grade=4.5,
        ask_count=2,
        allowed_ask_count=4,
    )


def test_exam_result_persisted(tmp_path):
    store = ResultStore(str(tmp_path / "data"))
    result = _result()
    store.save(result)

    read_back = store.get(result.id)
    assert isinstance(read_back, ExamResult)
    assert read_back.exam_attempt_id == result.exam_attempt_id
    assert read_back.exam_id == result.exam_id
    assert read_back.raw_score_50 == 44
    assert read_back.suggested_grade == 4.5
    assert read_back.ask_count == 2


def test_history_appended(tmp_path):
    history = HistoryStore(str(tmp_path / "data"))
    student = "student://s1"
    history.create_profile(student, confirmed=True)
    result = _result()
    history.append_exam_result(student, result)

    profile = history.get(student)
    assert profile is not None
    events = [e for e in profile.events if e.type == "exam_completed"]
    assert len(events) == 1
    event = events[0]
    assert event.result_id == result.id
    assert event.payload["exam_id"] == result.exam_id
    assert event.payload["exam_attempt_id"] == result.exam_attempt_id
    assert event.payload["suggested_grade"] == 4.5
    assert event.payload["ask_count"] == 2


class FailingStore:
    """Store stub whose every write fails, proving failures stay visible."""

    def __init__(self, label: str) -> None:
        self.label = label

    def save(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")

    def mark_completed(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")

    def append_exam_result(self, *_args, **_kwargs):
        raise OSError(f"{self.label} is read-only")


def test_finish_surfaces_persistence_failures(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    statement = tmp_path / "exam.md"
    statement.write_text(STATEMENT_MARKDOWN, encoding="utf-8")

    services = make_context(tmp_path, project, student="student://s1")
    services.context.attempt_id = "attempt://a-missing"

    action = ExamineAction(services, runner=OkRunner())
    action.start(
        ExamStartInput(
            statement=str(statement), project_id="project://p1", confirmed=True
        )
    )

    services.results = FailingStore("result store")
    services.attempts = FailingStore("attempt store")
    services.history = FailingStore("history store")

    finished = action.finish(ExamFinishInput(confirmed=True))
    joined = "\n".join(finished.result.limitations)
    assert "was NOT persisted" in joined
    assert "was NOT marked completed" in joined
    assert "NOT appended to history" in joined