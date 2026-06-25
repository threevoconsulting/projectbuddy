"""Deterministic fake LLM — powers CI, tests, and the no-models dev container.

It returns a valid Buddy JSON envelope chosen by simple keyword heuristics so the
text loop and face feel alive without any model. For tests that need to exercise
the parser's retry/fallback paths, pass ``scripted`` raw replies to be returned in
order before the heuristic kicks in.
"""

from __future__ import annotations

import json

from projectbuddy.models.llm.base import ChatMessage
from projectbuddy.protocol.llm_envelope import Emotion


def _heuristic_reply(user_text: str) -> str:
    text = user_text.lower()
    emotion = Emotion.happy
    say = "That sounds fun! Tell me more."
    remember: list[dict[str, str]] = []

    if any(w in text for w in ("space", "rocket", "planet", "star")):
        emotion = Emotion.excited
        say = "Rockets are SO cool! They blast fire to zoom up super fast. Want a space fact?"
    elif any(w in text for w in ("dino", "dinosaur", "rex", "stegosaurus")):
        emotion = Emotion.excited
        say = "Dinosaurs are amazing! The stegosaurus had cool plates on its back."
        remember = [{"key": "likes_dinosaurs", "value": "true"}]
    elif any(
        w in text for w in ("i won", "i did it", "i finished", "finished it", "got it", "i made it")
    ):
        emotion = Emotion.celebrating
        say = "Hooray! You did it! I'm SO proud of you. Want to try another?"
    elif any(w in text for w in ("story", "tell me a story", "once upon")):
        emotion = Emotion.happy
        say = "Once upon a time, a tiny star wished to be the brightest in the sky..."
    elif any(w in text for w in ("joke", "funny")):
        emotion = Emotion.celebrating
        say = "Why did the cookie go to the doctor? It felt crummy! Ha! Want another?"
    elif any(w in text for w in ("game", "let's play", "lets play", "play a", "i spy", "riddle")):
        emotion = Emotion.curious
        say = "Yes, let's play! I spy with my little eye something blue. Can you guess?"
    elif any(
        w in text
        for w in ("how do", "how does", "why do", "why does", "what is", "teach me", "learn")
    ):
        emotion = Emotion.thinking
        say = "Great thing to wonder about! What do you think? Then I'll tell you a fun fact."
    elif any(w in text for w in ("sad", "scared", "cry")):
        emotion = Emotion.sad
        say = "I'm sorry you feel that way. I'm right here with you. Want to talk about it?"
    elif "?" in text:
        emotion = Emotion.curious
        say = "Ooh, good question! What do you think the answer might be?"

    return json.dumps({"emotion": emotion.value, "say": say, "remember": remember})


class FakeLLMClient:
    def __init__(self, scripted: list[str] | None = None) -> None:
        self._scripted = list(scripted or [])
        self.calls: list[list[ChatMessage]] = []

    async def chat(self, messages: list[ChatMessage], *, json: bool = True) -> str:
        self.calls.append(messages)
        if self._scripted:
            return self._scripted.pop(0)
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        return _heuristic_reply(last_user)

    async def warmup(self) -> None:
        return None
