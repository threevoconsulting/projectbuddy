"""The fake LLM's keyword heuristics drive the offline/CI personality.

These assert the content-behaviour triggers (M6): stories, jokes, games, learning
nudges, and celebration map to the expected emotion so the no-models stack still
feels alive and the behaviours are regression-tested without a real model.
"""

from __future__ import annotations

import json

import pytest

from projectbuddy.models.llm.base import ChatMessage
from projectbuddy.models.llm.fake import FakeLLMClient
from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion


async def _reply(text: str) -> BuddyReply:
    """Run one heuristic turn and parse it through the real envelope validator."""
    msgs: list[ChatMessage] = [{"role": "user", "content": text}]
    raw = await FakeLLMClient().chat(msgs)
    return BuddyReply.model_validate_json(raw)


@pytest.mark.parametrize(
    ("text", "emotion"),
    [
        ("Tell me a story about a bunny", Emotion.happy),
        ("Do you know a joke?", Emotion.celebrating),
        ("Can we play a game?", Emotion.curious),
        ("Let's play I spy", Emotion.curious),
        ("How does a rainbow work?", Emotion.thinking),
        ("What is gravity?", Emotion.thinking),
        ("I won the game!", Emotion.celebrating),
        ("I did it all by myself", Emotion.celebrating),
        ("I feel sad today", Emotion.sad),
        ("I love rockets and space", Emotion.excited),
    ],
)
async def test_heuristic_emotions(text: str, emotion: Emotion) -> None:
    reply = await _reply(text)
    assert reply.emotion is emotion
    assert reply.say  # always speaks something


async def test_default_is_happy_and_valid_envelope() -> None:
    reply = await _reply("the grass is green")
    assert reply.emotion is Emotion.happy


async def test_scripted_replies_take_priority() -> None:
    llm = FakeLLMClient(scripted=['{"emotion": "sleepy", "say": "Yawn.", "remember": []}'])
    raw = await llm.chat([{"role": "user", "content": "tell me a joke"}])
    assert json.loads(raw)["emotion"] == "sleepy"
