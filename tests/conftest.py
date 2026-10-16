from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def mini_config_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "pyproject.toml")


@pytest.fixture
def sample_config(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        """
[project]
path = "."

[llm]
provider = "ollama"
model = "file-model"
base_url = "http://localhost:11434/v1"
temperature = 0.2
timeout_seconds = 120
max_output_tokens = 2048
max_context_tokens = 8192
max_attempts = 3

[tools]
timeout_seconds = 600
network = true
offline = false
static_kotlin = "detekt"
static_android = "lint"

[secrets]
api_key_env = "ADA_SENSEI_API_KEY"
""",
        encoding="utf-8",
    )
    return config


@pytest.fixture
def clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("ADA_SENSEI_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    return os.environ


def seed_learning_profile(
    data_dir,
    student_id: str,
    stage_id: str = "kotlin-fundamentals",
):
    """Persist a minimal LearningProfile (onboarded student) for TUI tests.

    First-run onboarding triggers only when no profile exists; tests for
    post-onboarding behavior seed one before resolving the student name.
    """
    from datetime import UTC, datetime

    from ada_sensei.learning.models import LearningProfile
    from ada_sensei.learning.stores import LearningProfileStore

    now = datetime.now(tz=UTC)
    store = LearningProfileStore(str(data_dir))
    store.save(
        LearningProfile(
            student_id=student_id,
            catalog_id="android-learning-path",
            catalog_version="1.2.0",
            current_stage_id=stage_id,
            created_at=now,
            updated_at=now,
        )
    )
    return store.get(student_id)


def seed_saved_locale(
    data_dir,
    student_id: str,
    locale: str = "en-US",
):
    """Persist a locale choice (returning student) for TUI tests.

    The first-run language gate opens only when no locale is saved; tests for
    post-language behavior seed one before resolving the student name.
    """
    from ada_sensei.locale.service import LocaleService
    from ada_sensei.locale.store import LocalePreferenceStore

    svc = LocaleService(LocalePreferenceStore(str(data_dir)))
    return svc.set_locale(student_id, locale)
