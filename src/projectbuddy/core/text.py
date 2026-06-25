"""Small text helpers for speech.

Buddy's lines are spoken aloud, so emoji/pictographs must be stripped — otherwise the
TTS engine reads them out ("smiling face", "rocket"). The system prompt also asks the
model not to use them; this is the deterministic backstop.
"""

from __future__ import annotations

import re

_EMOJI_RE = re.compile(
    "["
    "\U0001f000-\U0001faff"  # emoji, symbols & pictographs (incl. supplemental)
    "\U00002600-\U000027bf"  # misc symbols + dingbats
    "\U00002b00-\U00002bff"  # arrows, stars
    "\U00002190-\U000021ff"  # arrows block
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U0000200d"  # zero-width joiner
    "]+",
    flags=re.UNICODE,
)


def for_speech(text: str) -> str:
    """Remove emoji/pictographs and tidy whitespace so the line reads cleanly aloud."""
    cleaned = _EMOJI_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip()
