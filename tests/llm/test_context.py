from __future__ import annotations

from ada_sensei.llm.context import ContextManager


class Builder:
    @staticmethod
    def _long(n=2000):
        return "x" * n


def test_budget_eviction():
    manager = ContextManager(
        max_context_tokens=1024, conversation_budget=0.4, evidence_budget=0.4
    )
    conversation = [
        {"role": "user", "content": Builder._long()},
        {"role": "assistant", "content": Builder._long()},
    ]
    bundle = manager.build(system="sys", conversation=conversation)
    assert bundle.reduction.evicted
    assert bundle.reduction.notice is not None


def test_identity_priority():
    manager = ContextManager(
        max_context_tokens=512, conversation_budget=0.8, evidence_budget=0.1
    )
    conversation = [
        {"role": "user", "content": f"identity {Builder._long()}"},
        {"role": "user", "content": f"task {Builder._long()}"},
        {"role": "user", "content": f"history {Builder._long()}"},
    ]
    bundle = manager.build(system="sys", conversation=conversation)
    # system message (identity/active-task context) always preserved
    assert bundle.messages[0]["role"] == "system"
    assert len(bundle.messages) >= 1


def test_reduction_metadata():
    manager = ContextManager(
        max_context_tokens=1024, conversation_budget=0.4, evidence_budget=0.4
    )
    bundle = manager.build(
        system="sys",
        conversation=[
            {"role": "user", "content": Builder._long()},
            {"role": "user", "content": Builder._long()},
        ],
        summarize_fn=lambda msgs: "summarized",
    )
    reduction = bundle.reduction
    assert hasattr(reduction, "evicted")
    assert hasattr(reduction, "summarized")
    assert (
        reduction.notice is None
        or "summarized" in reduction.notice
        or "evicted" in reduction.notice
    )


def test_no_reduction_within_budget():
    manager = ContextManager(max_context_tokens=4096)
    bundle = manager.build(
        system="sys", conversation=[{"role": "user", "content": "hello"}]
    )
    assert not bundle.reduction.evicted
    assert not bundle.reduction.summarized
