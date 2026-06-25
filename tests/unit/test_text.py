"""Spoken text is emoji-free (TTS would otherwise read the emoji names)."""

from __future__ import annotations

from projectbuddy.core import safety
from projectbuddy.core.text import for_speech
from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion


def test_for_speech_strips_emoji_and_tidies() -> None:
    assert for_speech("Hooray! 🎉 You did it 😄") == "Hooray! You did it"
    assert for_speech("plain text") == "plain text"


def test_enforce_strips_emoji_from_spoken_line() -> None:
    reply = BuddyReply(emotion=Emotion.happy, say="Yay! 🚀🌟", remember=[])
    out = safety.enforce(reply)
    assert out.say == "Yay!"
    assert out.emotion is Emotion.happy
