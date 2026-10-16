"""Context-aware tutoring: guidance, context, and recommendations (spec 0011).

Covers REQ-001 (descriptions), REQ-007 (no invented facts), REQ-008/009
(justified + valid recommendations), REQ-010 (no auto-execution), REQ-011 (no
progression change), REQ-012 (bilingual parity), REQ-013 (safe failures).
"""

from __future__ import annotations

from ada_sensei.cli.action_registry import (
    action_guidance,
    action_ids,
    check_availability,
    get_actions,
)
from ada_sensei.tutoring import assemble_context, recommend_next


def _ctx(**overrides):
    base = {
        "student_id": "Ada",
        "stage_id": "kotlin-fundamentals",
        "stage_number": 1,
        "stage_name": "Kotlin Fundamentals",
        "stage_objective": "Write small Kotlin programs.",
        "action_id": "ask",
        "locale": "en-US",
        "project_active": True,
        "exam_active": False,
        "last_outcome": "ok",
    }
    base.update(overrides)
    return assemble_context(**base)


# -- REQ-001: selector guidance ------------------------------------------------


def test_every_action_has_bilingual_guidance_metadata():
    for action in get_actions():
        for locale in ("es-CO", "en-US"):
            assert action.label(locale), action.id
            assert action.description(locale), action.id
            assert action.hint(locale), action.id
            assert action.outcome(locale), action.id
            assert action.help(locale), action.id


def test_guidance_text_covers_what_what_to_provide_what_next():
    for action in get_actions():
        for locale in ("es-CO", "en-US"):
            text = action_guidance(action.id, locale)
            assert action.description(locale) in text
            assert action.outcome(locale) in text
            # Activation is always explained; never an undocumented gesture.
            assert "Enter" in text


def test_guidance_unknown_action_falls_back_to_activation_hint():
    text = action_guidance("no-such-action", "es-CO")
    assert "Enter" in text


# -- REQ-007: evidence-grounded context ----------------------------------------


def test_missing_context_stays_unknown():
    ctx = assemble_context(
        student_id=None,
        stage_id=None,
        stage_number=None,
        stage_name=None,
        stage_objective=None,
        action_id=None,
        locale=None,
        last_outcome="maybe",
    )
    assert ctx.stage_id is None
    assert ctx.stage_name is None
    assert ctx.stage_objective is None
    assert ctx.action_id is None
    assert ctx.last_outcome is None  # "maybe" is not invented into ok/error
    assert ctx.locale == "en-US"  # rendering fallback only


def test_fully_unknown_context_yields_no_recommendation():
    ctx = assemble_context(
        student_id=None,
        stage_id=None,
        stage_number=None,
        stage_name=None,
        stage_objective=None,
        action_id=None,
        locale="en-US",
    )
    assert recommend_next(ctx) is None


# -- REQ-008/009: justified, valid recommendations ------------------------------


def _assert_valid(ctx, rec):
    assert rec is not None
    assert rec.action_id in action_ids()
    available, _ = check_availability(
        rec.action_id,
        project_path="/p" if ctx.project_active else None,
        exam_active=ctx.exam_active,
        locale=ctx.locale,
    )
    assert available, rec.action_id
    label = rec.display(ctx.locale)
    assert rec.action_id in label  # stable id visible, not only translation
    return rec


def test_error_recommends_help_first():
    ctx = _ctx(last_outcome="error")
    rec = _assert_valid(ctx, recommend_next(ctx))
    assert rec.action_id == "help"


def test_evidenced_gaps_recommend_practice():
    ctx = _ctx(action_id="learn", mastery_gaps=("functions",))
    rec = _assert_valid(ctx, recommend_next(ctx))
    assert rec.action_id == "practice"


def test_study_interactions_reinforce_with_practice():
    for action_id in ("ask", "examples", "learn"):
        rec = _assert_valid(ctx := _ctx(action_id=action_id), recommend_next(ctx))
        assert rec.action_id == "practice"


def test_practice_with_project_checks_comprehension():
    rec = _assert_valid(
        ctx := _ctx(action_id="practice", project_active=True), recommend_next(ctx)
    )
    assert rec.action_id == "evaluate"


def test_practice_without_project_reviews_concepts():
    rec = _assert_valid(
        ctx := _ctx(action_id="practice", project_active=False), recommend_next(ctx)
    )
    assert rec.action_id == "learn"


def test_evaluate_routes_back_to_practice():
    rec = _assert_valid(
        ctx := _ctx(action_id="evaluate"), recommend_next(ctx)
    )
    assert rec.action_id == "practice"


def test_diagnose_routes_to_study():
    rec = _assert_valid(
        ctx := _ctx(action_id="diagnose"), recommend_next(ctx)
    )
    assert rec.action_id == "learn"


def test_active_exam_and_meta_actions_yield_no_recommendation():
    assert recommend_next(_ctx(exam_active=True)) is None
    assert recommend_next(_ctx(action_id="language")) is None
    assert recommend_next(_ctx(action_id="help")) is None
    assert recommend_next(_ctx(action_id=None)) is None


def test_recommendation_sweep_never_returns_unsupported_action():
    locales = ("es-CO", "en-US")
    actions = [*(a.id for a in get_actions()), None]
    for locale in locales:
        for action_id in actions:
            for outcome in ("ok", "error", None):
                for project in (True, False):
                    for exam in (True, False):
                        ctx = _ctx(
                            action_id=action_id,
                            locale=locale,
                            last_outcome=outcome,
                            project_active=project,
                            exam_active=exam,
                        )
                        rec = recommend_next(ctx)
                        if rec is not None:
                            _assert_valid(ctx, rec)


# -- REQ-010: student agency — recommendations never execute --------------------


def test_recommendation_is_data_only():
    rec = recommend_next(_ctx())
    assert rec is not None
    assert not hasattr(rec, "execute")
    assert not hasattr(rec, "run")
    assert isinstance(rec.params, dict)


# -- REQ-011: progression safeguards --------------------------------------------


def test_recommendation_does_not_mutate_progress(tmp_path):
    from datetime import UTC, datetime

    from ada_sensei.learning.models import LearningProfile
    from ada_sensei.learning.stores import LearningProfileStore

    now = datetime.now(tz=UTC)
    store = LearningProfileStore(str(tmp_path))
    store.save(
        LearningProfile(
            student_id="Ada",
            catalog_id="android-learning-path",
            catalog_version="1.2.0",
            current_stage_id="kotlin-fundamentals",
            created_at=now,
            updated_at=now,
        )
    )
    ctx = _ctx()
    for _ in range(5):
        rec = recommend_next(ctx)
        if rec is not None:
            rec.display("es-CO")
            rec.display("en-US")
    assert store.get("Ada").current_stage_id == "kotlin-fundamentals"


# -- REQ-012: bilingual parity ---------------------------------------------------


def test_recommendation_bilingual_and_score_independent():
    ctx_es = _ctx(locale="es-CO")
    ctx_en = _ctx(locale="en-US")
    rec_es = recommend_next(ctx_es)
    rec_en = recommend_next(ctx_en)
    assert rec_es is not None and rec_en is not None
    assert rec_es.action_id == rec_en.action_id  # same decision both locales
    assert rec_es.display("es-CO") != rec_en.display("en-US")
    assert "practice" in rec_es.display("es-CO")
    # Scores never influence the recommendation.
    assert (
        recommend_next(_ctx(last_score=1.0)).action_id
        == recommend_next(_ctx(last_score=4.0)).action_id
    )
