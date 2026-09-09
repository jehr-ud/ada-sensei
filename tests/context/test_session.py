from __future__ import annotations

from ada_sensei.context import SessionContext
from ada_sensei.models import AssistanceLevel


def test_holds_state(tmp_path):
    ctx = SessionContext(data_dir=str(tmp_path))
    ctx.set_student("student://s1")
    ctx.set_project("/tmp/sample-project")
    ctx.set_exercise("exercise://e1")
    ctx.add_turn("user", "hello")
    ctx.advance_assistance()

    assert ctx.student_id == "student://s1"
    assert ctx.project_id is not None
    assert ctx.project_id.startswith("project://")
    assert ctx.attempt_id == ""
    assert ctx.current_exercise_id == "exercise://e1"
    assert ctx.assistance_level == AssistanceLevel.hint
    assert len(ctx.conversation) == 1


def test_resume(tmp_path):
    data_dir = str(tmp_path)
    first = SessionContext(data_dir=data_dir)
    first.set_student("student://s2")
    first.set_exercise("exercise://e2")
    first.advance_assistance()
    first.add_turn("user", "what is state?")
    first.persist()

    second = SessionContext(data_dir=data_dir)
    second.set_student("student://s2")
    assert second.current_exercise_id == "exercise://e2"
    assert second.assistance_level == AssistanceLevel.hint
    assert len(second.conversation) == 1
