"""The active project must reach the actions that evaluate it."""

from __future__ import annotations

from ada_sensei.cli.commands import ProjectCommand
from ada_sensei.cli.router import Router
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        return "{}"


def test_project_command_updates_config_and_session(tmp_path):
    project = tmp_path / "android-app"
    project.mkdir()
    config = Config(project={"path": "."})
    config.data_dir = tmp_path / "data"
    config.cache_dir = tmp_path / "cache"
    router = Router(config=config, client=FakeClient())

    result = router.dispatch(ProjectCommand(path=str(project)))

    assert result.path == str(project.resolve())
    assert router.config.project.path == str(project.resolve())
    assert router.context.project_path == str(project.resolve())
    assert router.context.project_id == result.project_id
