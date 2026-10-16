"""Locale propagation and locale-independent scoring (RQ-LNG-010/012).

- The active locale reaches Teacher, Planner, Evaluator, and Trainer through
  the existing agent contracts (machine fields stay language-neutral).
- Identical evidence yields identical progression decisions in both locales.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ada_sensei.agents.contracts import AgentRole
from ada_sensei.cli.commands import AskCommand


def _teacher_with_mocks(tmp_path):
    from ada_sensei.agents.evaluator import EvaluatorAgent
    from ada_sensei.agents.planner import PlannerAgent
    from ada_sensei.agents.stores import AgentInvocationStore
    from ada_sensei.agents.teacher import TeacherAgent
    from ada_sensei.agents.trainer import TrainerAgent
    from ada_sensei.cli.commands import MetaResult
    from ada_sensei.learning.stores import LearningProfileStore
    from ada_sensei.locale.service import LocaleService
    from ada_sensei.locale.store import LocalePreferenceStore

    planner = MagicMock(spec=PlannerAgent)
    evaluator = MagicMock(spec=EvaluatorAgent)
    trainer = MagicMock(spec=TrainerAgent)
    for specialist in (planner, evaluator, trainer):
        specialist.run.side_effect = lambda ctx, res: MagicMock(
            agent_id=AgentRole.PLANNER,
            status=MagicMock(value="ok"),
            summary="ok",
            structured_payload=MagicMock(
                current_stage_id=None,
                recommended_next_activity=None,
                mastery_gaps=[],
                progression_decision_ref=None,
                explanation="",
            ),
        )
    mock_services = MagicMock()
    mock_services.config.llm.model = "test-model"
    teacher = TeacherAgent(
        services=mock_services,
        planner=planner,
        evaluator=evaluator,
        trainer=trainer,
        locale_service=LocaleService(LocalePreferenceStore(tmp_path)),
        invocation_store=AgentInvocationStore(tmp_path),
        profile_store=LearningProfileStore(tmp_path),
    )
    return teacher, planner, evaluator, trainer, MetaResult(message="done")


def test_active_locale_reaches_all_specialists(tmp_path):
    from ada_sensei.locale.service import LocaleService
    from ada_sensei.locale.store import LocalePreferenceStore

    teacher, planner, evaluator, trainer, result = _teacher_with_mocks(tmp_path)
    LocaleService(LocalePreferenceStore(str(tmp_path))).set_locale(
        "student://ana", "es-CO"
    )
    ctx = MagicMock()
    ctx.student_id = "student://ana"
    ctx.project_id = None
    ctx.exam_attempt_id = None
    with patch.object(teacher, "_execute_action", return_value=(result, None)):
        decision = teacher.handle(AskCommand(question="hola?"), ctx)
    assert decision.locale == "es-CO"
    for specialist in (planner, evaluator, trainer):
        agent_ctx = specialist.run.call_args[0][0]
        assert agent_ctx.locale == "es-CO"


def test_identical_evidence_decides_identically_in_both_locales():
    from datetime import UTC, datetime

    from ada_sensei.learning.catalog import LearningCatalogLoader
    from ada_sensei.learning.models import (
        CriterionResult,
        DimensionResult,
        MasteryAssessment,
    )
    from ada_sensei.learning.progression import ProgressionPolicyEngine
    from ada_sensei.urns import URN

    loader = LearningCatalogLoader()
    engine = ProgressionPolicyEngine()
    statuses = []
    for locale in ("es-CO", "en-US"):
        policy = loader.load_policy(locale)
        rubrics = loader.load_rubrics(locale)
        rubric = loader.get_rubric_for_stage("kotlin-fundamentals", rubrics)
        refs = ["source_code://x.kt"]
        assessment = MasteryAssessment(
            id=URN.make("learning"),
            student_id="s",
            project_id="p",
            stage_id="kotlin-fundamentals",
            rubric_id=rubric.id,
            rubric_version=rubric.version,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            catalog_version="1.2.0",
            dimension_results=[
                DimensionResult(
                    dimension_id=d.id,
                    score=3.5,
                    criterion_results=[
                        CriterionResult(
                            criterion_id=c.id, score=3.5, evidence_refs=refs
                        )
                        for c in d.criteria
                    ],
                    evidence_refs=refs,
                )
                for d in rubric.dimensions
            ],
            overall_score=3.5,
            evidence_refs=refs,
            exit_challenge_completed=True,
            comprehension_check_completed=True,
            created_at=datetime.now(tz=UTC),
        )
        decision = engine.evaluate(assessment, rubric, policy, next_stage_id="s2")
        statuses.append(
            (decision.status, [g.passed for g in decision.gate_results])
        )
    assert statuses[0] == statuses[1]
    assert statuses[0][0] == "READY"
