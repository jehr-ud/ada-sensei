from __future__ import annotations

import io

import pytest
from ada_sensei.cli.errors import CLIError
from ada_sensei.cli.parser import CommandParser
from ada_sensei.cli.router import Router
from ada_sensei.cli.shell import Shell
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


def test_help_lists_commands(tmp_path):
    router = Fixtures.make_router(tmp_path)
    out = io.StringIO()
    shell = Shell(router, inp=io.StringIO(), out=out)
    shell.dispatch(CommandParser.parse_line("/help"))
    assert "practice" in out.getvalue()
    assert "/quit" in out.getvalue()
    assert "/hint" in out.getvalue()


def test_exit_stops_loop(tmp_path):
    router = Fixtures.make_router(tmp_path)
    shell = Shell(router, inp=io.StringIO(), out=io.StringIO())
    shell.running = True
    shell.dispatch(CommandParser.parse_line("/quit"))
    assert shell.running is False


def test_progressive_commands_parse(tmp_path):
    router = Fixtures.make_router(tmp_path)
    out = io.StringIO()
    Shell(router, inp=io.StringIO(), out=out)

    from ada_sensei.cli.commands import (
        HintCommand,
        MoreCommand,
        SolutionCommand,
    )

    assert isinstance(CommandParser.parse_line("/hint"), HintCommand)
    assert isinstance(CommandParser.parse_line("/more"), MoreCommand)
    assert isinstance(CommandParser.parse_line("/solution"), SolutionCommand)


def test_unknown_slash_error(tmp_path):
    router = Fixtures.make_router(tmp_path)
    shell = Shell(router, inp=io.StringIO(), out=io.StringIO())
    with pytest.raises(CLIError):
        shell.dispatch(CommandParser.parse_line("/bogus"))


def test_run_loop_processes_quit(tmp_path):
    router = Fixtures.make_router(tmp_path)
    out = io.StringIO()
    shell = Shell(router, inp=io.StringIO("/quit\n"), out=out)
    shell.run()
    assert shell.running is False
