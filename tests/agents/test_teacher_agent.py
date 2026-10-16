"""Tests for TeacherAgent orchestration (spec 009-agent-orchestration)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ada_sensei.agents.contracts import (
    AgentRole,
    AgentStatus,
    EvaluatorPayload,
    PlannerPayload,
    SpecialistResult,
    TrainerPayload,
)
from ada_sensei.agents.evaluator import EvaluatorAgent
from ada_sensei.agents.planner import PlannerAgent
from ada_sensei.agents.stores import AgentInvocationStore
from ada_sensei.agents.teacher import TeacherAgent
from ada_sensei.agents.trainer import TrainerAgent
from ada_sensei.learning.stores import (
    LearningProfileStore,
)
from ada_sensei.locale.service import LocaleService
from ada_sensei.locale.store import LocalePreferenceStore
from ada_sensei.urns import URN


def _dummy_specialist_result(role: AgentRole) -> SpecialistResult:
    payloads = {
        AgentRole.PLANNER: PlannerPayload(
            current_stage_id="kotlin-fundamentals",
            recommended_next_activity="practice",
            mastery_gaps=[],
            progression_decision_ref=None,
            learning_event_id=URN.make("learning"),
        ),
        AgentRole.EVALUATOR: EvaluatorPayload(
            diagnostic_signal=None,
            assessment_result_ref=None,
            criterion_gaps=[],
            limitations=[],
        ),
        AgentRole.TRAINER: TrainerPayload(
            explanation="Great question!",
            practice_task=None,
            hints=[],
            recommended_resources=[],
        ),
    }
    return SpecialistResult(
        agent_id=role,
        invocation_id=URN.make(f"{role.value}_inv"),
        status=AgentStatus.OK,
        summary="ok",
        structured_payload=payloads[role],
    )


def _make_teacher(tmp_path: Path):
    """Build a TeacherAgent with mocked specialists and a real invocation store."""
    planner = MagicMock(spec=PlannerAgent)
    planner.run.return_value = _dummy_specialist_result(AgentRole.PLANNER)

    evaluator = MagicMock(spec=EvaluatorAgent)
    evaluator.run.return_value = _dummy_specialist_result(AgentRole.EVALUATOR)

    trainer = MagicMock(spec=TrainerAgent)
    trainer.run.return_value = _dummy_specialist_result(AgentRole.TRAINER)

    locale_store = LocalePreferenceStore(tmp_path)
    locale_svc = LocaleService(locale_store)
    invocation_store = AgentInvocationStore(tmp_path)
    profile_store = LearningProfileStore(tmp_path)

    # Mock services and router
    mock_services = MagicMock()
    mock_services.config.llm.model = "qwen2.5"
    mock_services.config.resolved_data_dir = tmp_path

    # Mock the router dispatch so we don't need a real LLM
    from ada_sensei.cli.commands import MetaResult
    mock_result = MetaResult(message="mock action result")

    teacher = TeacherAgent(
        services=mock_services,
        planner=planner,
        evaluator=evaluator,
        trainer=trainer,
        locale_service=locale_svc,
        invocation_store=invocation_store,
        profile_store=profile_store,
    )
    return teacher, planner, evaluator, trainer, mock_result


def test_each_specialist_invoked_exactly_once(tmp_path):
    """Spec 009: every student-facing action invokes all three specialists exactly once."""
    teacher, planner, evaluator, trainer, mock_result = _make_teacher(tmp_path)

    from ada_sensei.cli.commands import AskCommand

    ctx = MagicMock()
    ctx.student_id = "student://alice"
    ctx.project_id = None

    cmd = AskCommand(question="Why does LazyColumn not update?")

    # Patch the router dispatch to avoid real LLM
    with patch.object(teacher, "_execute_action", return_value=(mock_result, None)):
        decision = teacher.handle(cmd, ctx)

    planner.run.assert_called_once()
    evaluator.run.assert_called_once()
    trainer.run.assert_called_once()


def test_failed_specialist_marked_as_failed_not_raised(tmp_path):
    """Spec 009: a crashed specialist is recorded as FAILED; orchestration continues."""
    teacher, planner, evaluator, trainer, mock_result = _make_teacher(tmp_path)

    # Make evaluator crash
    evaluator.run.side_effect = RuntimeError("evaluator exploded")

    from ada_sensei.cli.commands import AskCommand

    ctx = MagicMock()
    ctx.student_id = "student://alice"
    ctx.project_id = None
    cmd = AskCommand(question="test question")

    with patch.object(teacher, "_execute_action", return_value=(mock_result, None)):
        decision = teacher.handle(cmd, ctx)

    # Should not raise; should have a FAILED entry
    failed = [r for r in decision.specialist_results if r.status == AgentStatus.FAILED]
    assert any(r.agent_id == AgentRole.EVALUATOR for r in failed)


def test_final_response_is_not_empty(tmp_path):
    teacher, planner, evaluator, trainer, mock_result = _make_teacher(tmp_path)

    from ada_sensei.cli.commands import AskCommand

    ctx = MagicMock()
    ctx.student_id = "student://alice"
    ctx.project_id = None
    cmd = AskCommand(question="explain ViewModels")

    with patch.object(teacher, "_execute_action", return_value=(mock_result, None)):
        decision = teacher.handle(cmd, ctx)

    assert decision.final_response
    assert len(decision.final_response) > 0


def test_no_duplicate_action_execution(tmp_path):
    """Action must execute exactly once per handle() call."""
    teacher, planner, evaluator, trainer, mock_result = _make_teacher(tmp_path)

    from ada_sensei.cli.commands import AskCommand

    ctx = MagicMock()
    ctx.student_id = "student://alice"
    ctx.project_id = None
    cmd = AskCommand(question="explain coroutines")

    call_count = 0

    def mock_execute(command, session_ctx):
        nonlocal call_count
        call_count += 1
        return mock_result, None

    teacher._execute_action = mock_execute

    teacher.handle(cmd, ctx)
    assert call_count == 1, "Action must execute exactly once"


def test_all_three_agents_present_in_decision(tmp_path):
    teacher, planner, evaluator, trainer, mock_result = _make_teacher(tmp_path)

    from ada_sensei.cli.commands import PracticeCommand

    ctx = MagicMock()
    ctx.student_id = "student://alice"
    ctx.project_id = None
    cmd = PracticeCommand(topic="compose-state")

    with patch.object(teacher, "_execute_action", return_value=(mock_result, None)):
        decision = teacher.handle(cmd, ctx)

    agent_ids = {r.agent_id for r in decision.specialist_results}
    assert AgentRole.PLANNER in agent_ids
    assert AgentRole.EVALUATOR in agent_ids
    assert AgentRole.TRAINER in agent_ids
