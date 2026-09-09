from __future__ import annotations

from ada_sensei.models import StudentProfile
from ada_sensei.storage import HistoryStore
from ada_sensei.storage.history import ConfirmationRequiredError


def test_roundtrip(tmp_path):
    store = HistoryStore(str(tmp_path))
    store.create_profile("student://alice", confirmed=True)
    profile = store.get("student://alice")
    assert profile is not None and isinstance(profile, StudentProfile)
    assert store.has("student://alice")
    assert store.get("student://nobody") is None


def test_create_requires_confirmation(tmp_path):
    store = HistoryStore(str(tmp_path))
    try:
        store.create_profile("student://bob")
    except ConfirmationRequiredError:
        pass
    else:
        raise AssertionError("expected ConfirmationRequiredError")
    assert not store.has("student://bob")


def test_append_evaluation_outcome(tmp_path):
    from ada_sensei.models import EvaluationResult

    store = HistoryStore(str(tmp_path))
    store.create_profile("student://alice", confirmed=True)
    result = EvaluationResult(attempt_id="attempt://a", overall_score=88.0)
    store.append_evaluation("student://alice", result)
    profile = store.get("student://alice")
    assert any(e.type == "evaluation_completed" for e in profile.events)


def test_set_name_roundtrip(tmp_path):
    store = HistoryStore(str(tmp_path))
    store.create_profile("student://alice", confirmed=True)
    store.set_name("student://alice", "Alice")
    profile = store.get("student://alice")
    assert profile.name == "Alice"


def test_set_name_noop_without_profile(tmp_path):
    store = HistoryStore(str(tmp_path))
    store.set_name("student://ghost", "Ghost")
    assert store.get("student://ghost") is None
