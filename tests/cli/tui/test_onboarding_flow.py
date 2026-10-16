"""TUI first-run onboarding flow (spec 008, RQ-LRN-004/005).

New students without a learning profile see the dynamic catalog stage list
and choose diagnose / stage / skip. Returning students skip onboarding.
Slash commands keep working while onboarding is pending.
"""

from __future__ import annotations

import asyncio

from ada_sensei.cli.router import Router
from ada_sensei.cli.tui.app import AdaSenseiTUI
from ada_sensei.cli.tui.widgets import PromptArea
from ada_sensei.config import Config
from ada_sensei.learning.stores import LearningProfileStore
from ada_sensei.llm.base import LLMClient

from conftest import seed_learning_profile, seed_saved_locale


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        from ada_sensei.models import Answer

        return Answer(id="answer://a1", response="hello").model_dump_json()


def make_app(tmp_path) -> AdaSenseiTUI:
    config = Config(project={"path": str(tmp_path / "p")})
    config.data_dir = tmp_path
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())
    return AdaSenseiTUI(router=router)


def mounted(tmp_path, fn):
    async def _run():
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            seed_saved_locale(tmp_path, "Ada")  # language decided; onboarding shows
            app._resolve_pending_name("Ada")
            await pilot.pause()
            return await fn(app, pilot)

    return asyncio.run(_run())


def test_first_run_shows_dynamic_stage_list(tmp_path):
    async def check(app, pilot):
        assert app._pending_onboarding is True
        joined = "\n".join(app.ui_state.messages)
        assert "Learning stages:" in joined
        assert "1. Kotlin Fundamentals" in joined
        assert "9. Independent Projects" in joined
        return True

    assert mounted(tmp_path, check)


def test_choose_stage_by_number_persists_profile(tmp_path):
    async def check(app, pilot):
        app._process_line("6")
        await pilot.pause()
        assert app._pending_onboarding is False
        profile = LearningProfileStore(str(tmp_path)).get("Ada")
        assert profile is not None
        assert profile.current_stage_id == "android-basic-application"
        assert profile.mastered_stages == []
        assert any("6" in m for m in app.ui_state.messages)
        return True

    assert mounted(tmp_path, check)


def test_invalid_choice_stays_pending_then_recovers(tmp_path):
    async def check(app, pilot):
        app._process_line("cobol-99")
        await pilot.pause()
        assert app._pending_onboarding is True
        assert LearningProfileStore(str(tmp_path)).get("Ada") is None
        app._process_line("2")
        await pilot.pause()
        assert app._pending_onboarding is False
        assert (
            LearningProfileStore(str(tmp_path)).get("Ada").current_stage_id
            == "android-project-structure"
        )
        return True

    assert mounted(tmp_path, check)


def test_unmet_prerequisites_disclosed(tmp_path):
    async def check(app, pilot):
        app._process_line("3")
        await pilot.pause()
        joined = "\n".join(app.ui_state.messages)
        assert "android-project-structure" in joined
        assert "NOT" in joined  # never marked as mastered
        profile = LearningProfileStore(str(tmp_path)).get("Ada")
        assert profile.mastered_stages == []
        return True

    assert mounted(tmp_path, check)


def test_skip_uses_default_stage(tmp_path):
    async def check(app, pilot):
        app._process_line("skip")
        await pilot.pause()
        assert app._pending_onboarding is False
        assert (
            LearningProfileStore(str(tmp_path)).get("Ada").current_stage_id
            == "kotlin-fundamentals"
        )
        return True

    assert mounted(tmp_path, check)


def test_diagnose_path_flags_diagnostic(tmp_path):
    async def check(app, pilot):
        app._process_line("diagnose")
        await pilot.pause()
        assert app._pending_onboarding is False
        profile = LearningProfileStore(str(tmp_path)).get("Ada")
        assert profile.diagnostic_completed is True
        return True

    assert mounted(tmp_path, check)


def test_slash_commands_bypass_onboarding(tmp_path):
    async def check(app, pilot):
        assert app._pending_onboarding is True
        app._process_line("/help")
        await pilot.pause()
        assert app._pending_onboarding is True  # still pending afterwards
        return True

    assert mounted(tmp_path, check)


def test_returning_student_skips_onboarding(tmp_path):
    async def _run():
        seed_saved_locale(tmp_path, "Ada")
        seed_learning_profile(tmp_path, "Ada")
        app = make_app(tmp_path)
        async with app.run_test(size=(80, 24)) as pilot:
            app._resolve_pending_name("Ada")
            await pilot.pause()
            return app._pending_onboarding is False

    assert asyncio.run(_run())


def test_onboarding_input_area_stays_usable(tmp_path):
    async def check(app, pilot):
        area = app.query_one("#input", PromptArea)
        assert area is not None
        assert app._pending_onboarding is True
        return True

    assert mounted(tmp_path, check)
