"""Post-generation child-safety filter (M5).

Every line Buddy is about to speak passes through :func:`enforce`; the same
:func:`check` also screens the child's transcript so unsafe *topics* are redirected
before they ever reach the model. This is a deny-list grouped by category — fast,
deterministic, and CI-testable. A local classifier could be added behind the same
seam later, but a curated list is the dependable backstop and is what the red-team
gate (``make redteam``) holds to 100%.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion

# Deny-list grouped by category. Conservative on purpose: for a young child, a false
# block (gentle redirect) is far cheaper than a false allow. Expand as the red-team
# corpus grows — keep tests/fixtures/redteam.txt in lockstep.
_DENY_TERMS: dict[str, list[str]] = {
    "violence": ["kill", "murder", "stab", "shoot", "blood", "gore", "fight", "die", "dead"],
    "weapons": ["gun", "knife", "weapon", "bomb", "bullet"],
    "self_harm": ["suicide", "self-harm", "self harm", "hurt myself", "cut myself"],
    "sexual": ["sex", "sexy", "porn", "naked", "nude"],
    "substances": ["drug", "cocaine", "heroin", "weed", "alcohol", "beer", "wine", "vape"],
    "profanity": ["damn", "hell", "crap", "stupid", "idiot", "shut up"],
    "scary": ["nightmare", "demon", "ghost", "monster", "creepy", "scary"],
}
_ALL_TERMS = sorted({t for terms in _DENY_TERMS.values() for t in terms}, key=len, reverse=True)

# Match a whole word/phrase with an optional trailing plural "s" (drug → drugs); word
# boundaries keep "hell" from matching "hello".
_DENY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _ALL_TERMS) + r")s?\b", re.IGNORECASE
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
