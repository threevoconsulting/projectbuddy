from __future__ import annotations

import pytest
from pydantic import ValidationError

from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion


def test_accepts_valid_envelope() -> None:
    reply = BuddyReply.model_validate(
        {"emotion": "curious", "say": "Why is the sky blue?", "remember": []}
    )
    assert reply.emotion is Emotion.curious


def test_remember_defaults_to_empty() -> None:
    reply = BuddyReply.model_validate({"emotion": "happy", "say": "Hi"})
    assert reply.remember == []


def test_rejects_unknown_emotion() -> None:
    with pytest.raises(ValidationError):
        BuddyReply.model_validate({"emotion": "grumpy", "say": "hi"})


def test_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BuddyReply.model_validate({"emotion": "happy", "say": "hi", "oops": 1})


def test_rejects_empty_say() -> None:
    with pytest.raises(ValidationError):
        BuddyReply.model_validate({"emotion": "happy", "say": ""})
