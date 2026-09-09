from __future__ import annotations

import pytest
from ada_sensei.cli.commands import AskCommand
from ada_sensei.cli.errors import CLIError
from ada_sensei.cli.parser import CommandParser
from ada_sensei.cli.router import Router
from ada_sensei.config import Config
from ada_sensei.llm.base import LLMClient


class FakeClient(LLMClient):
    def chat(self, messages, *, model=None, temperature=None):
        return "ok"

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        from ada_sensei.models import Answer

        return Answer(id="answer://a1", response="hello").model_dump_json()


class Fixtures:
    @staticmethod
    def make_router(tmp_path) -> Router:
        config = Config(project={"path": str(tmp_path / "p")})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        return Router(config=config, client=FakeClient())


def test_no_student_command(tmp_path):
    # Identity comes from the name received at session start; there is no
    # /student or `student` command anymore.
    for line in ("/student alice", "student alice", "--student alice practice"):
        with pytest.raises(CLIError):
            CommandParser.parse_line(line)


def test_identity_never_inferred(tmp_path):
    router = Fixtures.make_router(tmp_path)
    # A prompt that mentions a person's name must not bind any identity.
    ask_inv = CommandParser.parse_line("ask Explain MVVM to sam")
    assert isinstance(ask_inv, AskCommand)
    assert router.context.student_id is None


def test_name_sets_identity_in_welcome(tmp_path):
    # The TUI welcome greeting binds the received name as the identity.
    router = Fixtures.make_router(tmp_path)
    assert router.context.student_id is None
    router.context.set_student("alice")
    assert router.context.student_id == "alice"