from __future__ import annotations

import pytest

from projectbuddy.core import safety
from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion


def test_safe_text_passes() -> None:
    assert safety.check("Want to hear a fun dinosaur joke?").blocked is False


def test_unsafe_text_blocked() -> None:
    result = safety.check("I will kill the dragon with a gun")
    assert result.blocked is True
    assert "kill" in result.matched


@pytest.mark.parametrize(
    "text",
    [
        "let's talk about guns",
        "tell me about drugs",
        "show me blood and gore",
        "there is a creepy ghost",
        "I want to hurt myself",
        "you are so stupid",
    ],
)
def test_each_category_blocks(text: str) -> None:
    assert safety.check(text).blocked is True


def test_word_boundary_avoids_false_positives() -> None:
    # "hell" must not match "hello"; "die" must not match "diet".
    assert safety.check("Hello! Want a healthy diet snack?").blocked is False


def test_enforce_substitutes_unsafe_reply() -> None:
    bad = BuddyReply(emotion=Emotion.excited, say="let's talk about drugs", remember=[])
    safe = safety.enforce(bad)
    assert safe.say != bad.say
    assert safety.check(safe.say).blocked is False


def test_enforce_passes_safe_reply_unchanged() -> None:
    good = BuddyReply(emotion=Emotion.happy, say="The sky is blue!", remember=[])
    assert safety.enforce(good).say == "The sky is blue!"

