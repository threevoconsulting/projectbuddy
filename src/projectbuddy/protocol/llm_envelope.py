"""The structured output the LLM must return — the single source of truth.

Buddy's model is instructed to reply with ONLY this JSON object (TDD Appendix B)::

    {
      "emotion": "excited",
      "say": "A stegosaurus? So cool! Want to hear a dino joke?",
      "remember": [{"key": "favorite_dinosaur", "value": "stegosaurus"}]
    }

The backend validates every reply against :class:`BuddyReply`. On failure the parser
retries once with a stricter instruction, then falls back to a safe default.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Emotion(StrEnum):
    """The eight expression states the face engine can render."""

    happy = "happy"
    curious = "curious"
    thinking = "thinking"
    excited = "excited"
    confused = "confused"
    sleepy = "sleepy"
    sad = "sad"
    celebrating = "celebrating"


class Fact(BaseModel):
    """A durable preference/fact to persist as long-term memory."""

    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=400)


class BuddyReply(BaseModel):
    """A validated Buddy turn: an expression, the spoken line, and facts to remember."""

    model_config = {"extra": "forbid"}

    emotion: Emotion
    say: str = Field(min_length=1, max_length=1000)
    remember: list[Fact] = Field(default_factory=list)


# Used when the model output cannot be parsed/validated even after one retry.
SAFE_FALLBACK = BuddyReply(
    emotion=Emotion.curious,
    say="Hmm, can you say that again?",
    remember=[],
)
