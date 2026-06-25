from __future__ import annotations

import json

from projectbuddy.core.output_parser import lenient_parse, parse_reply, try_parse
from projectbuddy.models.llm.fake import FakeLLMClient
from projectbuddy.protocol.llm_envelope import Emotion


def test_try_parse_valid() -> None:
    raw = json.dumps({"emotion": "happy", "say": "Hi!", "remember": []})
    reply = try_parse(raw)
    assert reply is not None
    assert reply.emotion is Emotion.happy
    assert reply.say == "Hi!"


def test_try_parse_extracts_object_from_prose() -> None:
    raw = 'Sure! {"emotion": "excited", "say": "Wow!"} hope that helps'
    reply = try_parse(raw)
    assert reply is not None
    assert reply.emotion is Emotion.excited


def test_try_parse_rejects_bad_emotion() -> None:
    raw = json.dumps({"emotion": "angry", "say": "grr"})
    assert try_parse(raw) is None


def test_try_parse_rejects_garbage() -> None:
    assert try_parse("not json at all") is None


def test_lenient_parse_recovers_small_model_output() -> None:
    # Off-list emotion → happy, spoken line under "text", unknown keys dropped.
    raw = json.dumps({"emotion": "friendly", "text": "I'm Buddy!", "mood": "warm", "extra": 1})
    reply = lenient_parse(raw)
    assert reply is not None
    assert reply.emotion is Emotion.happy
    assert reply.say == "I'm Buddy!"


def test_lenient_parse_keeps_valid_emotion_and_facts() -> None:
    raw = 'ok: {"emotion":"excited","say":"Dinos!","remember":[{"key":"likes","value":"dino"}]}'
    reply = lenient_parse(raw)
    assert reply is not None
    assert reply.emotion is Emotion.excited and reply.remember[0].value == "dino"


def test_lenient_parse_needs_a_spoken_line() -> None:
    assert lenient_parse(json.dumps({"emotion": "happy"})) is None
    assert lenient_parse("no json here") is None


async def test_parse_reply_recovers_without_retry() -> None:
    # A small-model reply (extra keys / alt say key) should parse with NO retry call.
    llm = FakeLLMClient()
    raw = json.dumps({"emotion": "neutral", "message": "Hello there!"})
    reply = await parse_reply(raw, [{"role": "user", "content": "hi"}], llm)  # type: ignore[arg-type]
    assert reply.say == "Hello there!" and reply.emotion is Emotion.happy
    assert len(llm.calls) == 0  # recovered on the first pass, no extra LLM round-trip


async def test_parse_reply_retries_once_then_succeeds() -> None:
    # First output (raw) is garbage; the retry uses the fake's heuristic -> valid JSON.
    llm = FakeLLMClient()
    messages = [{"role": "user", "content": "tell me about space"}]
    reply = await parse_reply("garbage", messages, llm)  # type: ignore[arg-type]
    assert reply.emotion in set(Emotion)
    assert len(llm.calls) == 1  # exactly one retry call


async def test_parse_reply_falls_back_when_retry_also_fails() -> None:
    llm = FakeLLMClient(scripted=["still not json"])
    messages = [{"role": "user", "content": "hello"}]
    reply = await parse_reply("garbage", messages, llm)  # type: ignore[arg-type]
    assert reply.emotion is Emotion.curious
    assert reply.say == "Hmm, can you say that again?"
