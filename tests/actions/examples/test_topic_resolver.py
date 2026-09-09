from __future__ import annotations

import pytest
from ada_sensei.actions.examples import ExamplesAction, TopicResolver


def test_known_topic_resolution():
    resolver = TopicResolver(ExamplesAction.knowledge_root())
    topic, known = resolver.resolve("state")
    assert topic == "state"
    assert "state" in known


def test_topic_normalized():
    resolver = TopicResolver(ExamplesAction.knowledge_root())
    topic, _ = resolver.resolve("lazy column")
    assert topic == "lazycolumn"


def test_unknown_topic_error():
    resolver = TopicResolver(ExamplesAction.knowledge_root())
    with pytest.raises(Exception) as exc_info:
        resolver.resolve("quantum-flux")
    message = str(exc_info.value)
    assert "unknown topic" in message
    assert "known topics" in message


def test_known_topics_nonempty():
    resolver = TopicResolver(ExamplesAction.knowledge_root())
    assert len(resolver.known_topics()) > 0