from __future__ import annotations

import json
from pathlib import Path

from ada_sensei.actions.ask import AskAction, QuestionClassifier
from ada_sensei.actions.base import ActionServices
from ada_sensei.config import Config
from ada_sensei.context import SessionContext
from ada_sensei.llm.base import LLMClient
from ada_sensei.models import AssistanceLevel

ANSWER = {
    "id": "answer://a1",
    "question": "Why doesn't my LazyColumn update?",
    "classification": "debugging",
    "assistance_level": "conceptual_explanation",
    "response": (
        "Your LazyColumn does not update because the list state is held "
        "outside a ViewModel."
    ),
    "citations": ["MainViewModel.kt:24"],
    "uncertainty": False,
    "created_at": "2026-01-01T00:00:00Z",
}


class FakeClient(LLMClient):
    def __init__(self, payload=None):
        self.payload = payload if payload is not None else json.dumps(ANSWER)
        self.messages_seen = []

    def chat(self, messages, *, model=None, temperature=None):
        return ""

    def chat_structured(
        self, messages, *, model=None, json_schema=None, temperature=None
    ):
        self.messages_seen.append(messages)
        return self.payload


class Services:
    @staticmethod
    def make(tmp_path, student="student://s1", project_path=None):
        proj = project_path or tmp_path / "proj"
        proj.mkdir(parents=True, exist_ok=True)
        (proj / "MainViewModel.kt").write_text(
            "class MainViewModel { val items = mutableStateListOf() }\n",
            encoding="utf-8",
        )
        (proj / "MainScreen.kt").write_text(
            "@Composable fun MainScreen(vm: MainViewModel) { LazyColumn { } }\n",
            encoding="utf-8",
        )
        config = Config(project={"path": str(proj)})
        config.data_dir = tmp_path
        config.cache_dir = tmp_path / "cache"
        ctx = SessionContext(config=config, data_dir=tmp_path / "sess")
        ctx.set_student(student)
        from ada_sensei.storage.history import HistoryStore

        hstore = HistoryStore(str(tmp_path))
        hstore.create_profile(student, confirmed=True)
        client = FakeClient()
        return ActionServices.build(config, ctx, client), client, hstore


def test_accepts_question(tmp_path):
    services, client, _ = Services.make(tmp_path)
    result = AskAction(services).run("What is remember?")
    assert result.answer.response


def test_android_domain(tmp_path):
    services, client, _ = Services.make(tmp_path)
    AskAction(services).run("What is a ViewModel?")
    seen = " ".join(
        m.get("content", "")
        for messages in client.messages_seen
        for m in messages
    )
    assert "Android" in seen


def test_inspects_project(tmp_path):
    services, client, _ = Services.make(tmp_path, project_path=tmp_path / "proj")
    result = AskAction(services).run("Why doesn't my app update? code error in view")
    assert result.answer.citations


def test_classification(tmp_path):
    services, _, _ = Services.make(tmp_path)
    classifier = QuestionClassifier()
    assert classifier.classify("Why does my app crash?") == "debugging"
    assert classifier.classify("What is a composable?") == "conceptual"
    assert classifier.classify("How do I implement a ViewModel?") == "implementation"


def test_cites_evidence(tmp_path):
    services, client, _ = Services.make(tmp_path)
    result = AskAction(services).run("Debug why the list crashes")
    assert result.answer.citations


def test_progressive_levels(tmp_path):
    services, _, _ = Services.make(tmp_path)
    assert services.context.assistance_level == AssistanceLevel.guiding_question
    result = AskAction(services).run("What is state?")
    services.context.advance_assistance()
    assert services.context.assistance_level == AssistanceLevel.hint
    assert result.answer


def test_no_project_writes(tmp_path):
    services, _, _ = Services.make(tmp_path)
    proj = Path(services.config.project.path)
    before = {
        rel.name: rel.read_text(encoding="utf-8")
        for rel in proj.iterdir()
        if rel.suffix == ".kt"
    }
    AskAction(services).run("Why does my app crash?")
    after = {rel.name for rel in proj.iterdir() if rel.suffix == ".kt"}
    assert after == set(before) | after
    for name, content in before.items():
        assert (proj / name).read_text(encoding="utf-8") == content


def test_uncertainty_stated(tmp_path):
    answers = dict(ANSWER)
    answers["uncertainty"] = True
    services, client, _ = Services.make(tmp_path)
    client.payload = json.dumps(answers)
    result = AskAction(services).run("What is the exact cause?")
    assert result.answer.uncertainty is True


def test_follow_up_in_context(tmp_path):
    services, client, _ = Services.make(tmp_path)
    AskAction(services).run("What is remember?")
    AskAction(services).run("How does it differ from mutableStateOf?")
    user_contents = []
    for messages in client.messages_seen:
        for m in messages:
            if m["role"] == "user":
                user_contents.append(m["content"])
    assert len(user_contents) >= 2
    assert any("mutableStateOf" in c for c in user_contents)


def test_uses_student_profile(tmp_path):
    services, client, hstore = Services.make(tmp_path)
    hstore.add_weakness("student://s1", "state-and-lifecycle")
    AskAction(services).run("What is state?")
    seen = " ".join(
        m.get("content", "") for messages in client.messages_seen for m in messages
    )
    assert "state-and-lifecycle" in seen


def test_escalation_without_reclassify(tmp_path):
    services, client, _ = Services.make(tmp_path)
    first = AskAction(services).run("Debug why the list crashes")
    classification = first.answer.classification
    escalated = AskAction(services).escalate("solution")
    assert escalated.answer.classification == classification
    assert (
        services.context.assistance_level == AssistanceLevel.solution
    )
    # previous answer kept in context
    assert len(services.context.conversation) >= 2