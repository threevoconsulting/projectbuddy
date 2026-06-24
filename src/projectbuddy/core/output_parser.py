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
import re

from pydantic import ValidationError

from projectbuddy.models.llm.base import ChatMessage, LLMClient
from projectbuddy.protocol.llm_envelope import SAFE_FALLBACK, BuddyReply

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

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


async def parse_reply(raw: str, messages: list[ChatMessage], llm: LLMClient) -> BuddyReply:
    """Parse ``raw``; if invalid, retry the LLM once; else return the safe fallback."""
    reply = try_parse(raw)
    if reply is not None:
        return reply

    assistant_msg: ChatMessage = {"role": "assistant", "content": raw}
    retry_messages: list[ChatMessage] = [*messages, assistant_msg, _RETRY_INSTRUCTION]
    retry_raw = await llm.chat(retry_messages, json=True)
    reply = try_parse(retry_raw)
    if reply is not None:
        return reply

    return SAFE_FALLBACK.model_copy(deep=True)
