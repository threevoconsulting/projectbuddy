"""Post-generation child-safety filter (baseline; hardened in M5).

Every line Buddy is about to speak passes through :func:`check`. This baseline is a
deny-list of clearly age-inappropriate terms; M5 expands it with the red-team corpus
and, optionally, a local classifier. The seam is stable: callers only see a
:class:`SafetyResult` and use ``safe_reply`` when ``blocked`` is true.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion

# Baseline deny-list. Intentionally conservative; expanded with the red-team set in M5.
_DENY_TERMS = [
    "kill",
    "suicide",
    "sex",
    "sexy",
    "porn",
    "drug",
    "cocaine",
    "gun",
    "weapon",
    "blood",
    "gore",
    "damn",
    "hell",
]
# Allow a trailing plural "s" (drug → drugs) without matching unrelated words
# (the word boundary keeps "hell" from matching "hello").
_DENY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _DENY_TERMS) + r")s?\b", re.IGNORECASE
)

_SAFE_SUBSTITUTE = BuddyReply(
    emotion=Emotion.curious,
    say="Let's talk about something fun instead! What's your favorite animal?",
    remember=[],
)


@dataclass(frozen=True)
class SafetyResult:
    blocked: bool
    matched: tuple[str, ...] = ()


def check(text: str) -> SafetyResult:
    """Return whether ``text`` should be blocked, and which terms triggered it."""
    matches = tuple(m.group(0).lower() for m in _DENY_RE.finditer(text))
    return SafetyResult(blocked=bool(matches), matched=matches)


def enforce(reply: BuddyReply) -> BuddyReply:
    """Return ``reply`` unchanged if safe, else a safe substitute."""
    if check(reply.say).blocked:
        return _SAFE_SUBSTITUTE.model_copy(deep=True)
    return reply
