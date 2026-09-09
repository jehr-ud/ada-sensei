from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

MAX_CONTEXT_TOKENS = 8192
CONVERSATION_BUDGET = 0.4
EVIDENCE_BUDGET = 0.4
OUTPUT_BUDGET = 0.2


class TokenEstimator:
    @staticmethod
    def estimate(text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 4))

    @staticmethod
    def contents(messages: list[dict[str, str]]) -> list[str]:
        return [m.get("content", "") for m in messages]

    @staticmethod
    def tokens(contents: list[str]) -> int:
        return sum(TokenEstimator.estimate(c) for c in contents)

    @staticmethod
    def messages(
        system: str, conversation: list[dict[str, str]], evidence: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if evidence:
            payload = "\n\n".join(m.get("content", "") for m in evidence)
            messages.append(
                {"role": "user", "content": f"Context files/evidence:\n{payload}"}
            )
        messages.extend(conversation)
        return messages


@dataclass
class ContextReduction:
    evicted_conversation: int = 0
    evicted_evidence: int = 0
    summarized: bool = False
    llm_derived: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def evicted(self) -> bool:
        return self.evicted_conversation > 0 or self.evicted_evidence > 0

    @property
    def notice(self) -> str | None:
        if self.summarized:
            return (
                "context reduced and LLM-summarized "
                "(summaries are not objective evidence)"
            )
        if self.evicted:
            return (
                "context budget exceeded; older content was evicted deterministically"
            )
        return None


@dataclass
class ContextBundle:
    messages: list[dict[str, str]]
    reduction: ContextReduction


class ContextManager:
    def __init__(
        self,
        *,
        max_context_tokens: int = MAX_CONTEXT_TOKENS,
        conversation_budget: float = CONVERSATION_BUDGET,
        evidence_budget: float = EVIDENCE_BUDGET,
        output_budget: float = OUTPUT_BUDGET,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.conversation_budget = conversation_budget
        self.evidence_budget = evidence_budget
        self.output_budget = output_budget

    def _limits(self) -> tuple[int, int]:
        conversation_tokens = int(self.max_context_tokens * self.conversation_budget)
        evidence_tokens = int(self.max_context_tokens * self.evidence_budget)
        return conversation_tokens, evidence_tokens

    def build(
        self,
        *,
        system: str,
        conversation: list[dict[str, str]],
        evidence: list[dict[str, str]] | None = None,
        summarize_fn: Callable[[list[dict[str, str]]], str] | None = None,
    ) -> ContextBundle:
        evidence = evidence or []
        conversation_tokens, evidence_tokens = self._limits()
        reduction = ContextReduction()

        kept_conversation = list(conversation)
        used = TokenEstimator.tokens([system]) + TokenEstimator.tokens(
            TokenEstimator.contents(conversation)
        )
        while used > conversation_tokens and len(kept_conversation) > 1:
            kept_conversation.pop(0)
            reduction.evicted_conversation += 1
            used = TokenEstimator.tokens([system]) + TokenEstimator.tokens(
                TokenEstimator.contents(kept_conversation)
            )

        kept_evidence = list(evidence)
        used_evidence = TokenEstimator.tokens(
            TokenEstimator.contents(kept_evidence)
        )
        while used_evidence > evidence_tokens and len(kept_evidence) > 1:
            kept_evidence.pop(0)
            reduction.evicted_evidence += 1
            used_evidence = TokenEstimator.tokens(
                TokenEstimator.contents(kept_evidence)
            )

        messages = TokenEstimator.messages(system, kept_conversation, kept_evidence)

        total = (
            TokenEstimator.tokens([system])
            + used
            + used_evidence
            + int(self.max_context_tokens * self.output_budget)
        )
        if total > self.max_context_tokens and summarize_fn is not None:
            try:
                summary = summarize_fn(messages[-8:])
            except Exception:
                summary = ""
            if summary:
                reduction.summarized = True
                reduction.llm_derived = True
                messages = [m for m in messages if m["role"] == "system"] + [
                    {"role": "user", "content": f"[llm-derived summary] {summary}"}
                ]

        return ContextBundle(messages=messages, reduction=reduction)
