"""Turn raw LLM text into a validated :class:`BuddyReply`.

Strategy (TDD Appendix B):

1. Parse + validate the raw reply against the envelope.
2. On failure, re-ask the LLM **once** with a stricter corrective instruction.
3. If it still fails, return the safe fallback expression + gentle line.

This keeps the rest of the system deterministic: downstream code always receives a
valid ``BuddyReply``.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from projectbuddy.models.llm.base import ChatMessage, LLMClient
from projectbuddy.protocol.llm_envelope import SAFE_FALLBACK, BuddyReply, Emotion, Fact

_log = logging.getLogger("uvicorn.error")

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_EMOTIONS = {e.value for e in Emotion}
# Small models scatter the spoken line under various keys — accept the common ones.
_SAY_KEYS = ("say", "text", "message", "response", "reply", "speech", "content")

_RETRY_INSTRUCTION: ChatMessage = {
    "role": "user",
    "content": (
        "That was not valid. Reply with ONLY a single JSON object and nothing else, "
        'exactly: {"emotion": one of '
        "[happy, curious, thinking, excited, confused, sleepy, sad, celebrating], "
        '"say": a short sentence, "remember": a list (possibly empty).'
    ),
}


def try_parse(raw: str) -> BuddyReply | None:
    """Best-effort parse of one raw reply. Tolerates leading/trailing prose.

    Returns ``None`` if no valid envelope can be extracted.
    """
    candidates = [raw]
    match = _JSON_OBJECT.search(raw)
    if match:
        candidates.append(match.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        try:
            return BuddyReply.model_validate(data)
        except ValidationError:
            continue
    return None


def lenient_parse(raw: str) -> BuddyReply | None:
    """Best-effort recovery for small-model output (llama3.2:3b etc).

    Extracts the JSON object, then coerces it instead of rejecting on small mistakes:
    an off-list ``emotion`` becomes ``happy``; the spoken line is read from any of the
    common keys; unknown keys and malformed ``remember`` items are dropped. Returns
    ``None`` only when there is no usable spoken line.
    """
    match = _JSON_OBJECT.search(raw)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    emotion = str(data.get("emotion", "")).strip().lower()
    if emotion not in _EMOTIONS:
        emotion = "happy"

    say = ""
    for key in _SAY_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            say = value.strip()
            break
    if not say:
        return None

    remember: list[Fact] = []
    raw_mem = data.get("remember")
    if isinstance(raw_mem, list):
        for item in raw_mem:
            if isinstance(item, dict):
                k = str(item.get("key", "")).strip()
                v = str(item.get("value", "")).strip()
                if k and v:
                    remember.append(Fact(key=k[:80], value=v[:400]))

    try:
        return BuddyReply(emotion=Emotion(emotion), say=say[:1000], remember=remember)
    except ValidationError:
        return None


async def parse_reply(raw: str, messages: list[ChatMessage], llm: LLMClient) -> BuddyReply:
    """Parse ``raw`` (strict, then lenient); if still invalid retry once; else fall back."""
    reply = try_parse(raw) or lenient_parse(raw)
    if reply is not None:
        return reply

    _log.info("parser: reply not valid, retrying once. raw=%r", raw[:300])
    assistant_msg: ChatMessage = {"role": "assistant", "content": raw}
    retry_messages: list[ChatMessage] = [*messages, assistant_msg, _RETRY_INSTRUCTION]
    retry_raw = await llm.chat(retry_messages, json=True)
    reply = try_parse(retry_raw) or lenient_parse(retry_raw)
    if reply is not None:
        return reply

    _log.warning("parser: fell back to safe reply. raw=%r retry=%r", raw[:200], retry_raw[:200])
    return SAFE_FALLBACK.model_copy(deep=True)
