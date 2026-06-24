"""WebSocket frame models for ``/ws/converse`` (wired fully in M4).

Server → client during one turn, in this order (the face leads the voice)::

    {"type": "state",   "value": "listening"}
    {"type": "state",   "value": "thinking"}
    {"type": "emotion", "value": "excited"}      # face animates now
    {"type": "audio",   "chunk": "<base64 pcm>"} # TTS streams; mouth animates
    ...
    {"type": "final",   "transcript": "...", "say": "..."}

Defined here in M2 so the contract is stable and testable before the audio
pipeline lands.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from projectbuddy.protocol.llm_envelope import Emotion

ConversationState = Literal["idle", "listening", "thinking", "speaking"]


class StateFrame(BaseModel):
    type: Literal["state"] = "state"
    value: ConversationState


class EmotionFrame(BaseModel):
    type: Literal["emotion"] = "emotion"
    value: Emotion


class AudioFrame(BaseModel):
    type: Literal["audio"] = "audio"
    chunk: str  # base64-encoded PCM


class FinalFrame(BaseModel):
    type: Literal["final"] = "final"
    transcript: str
    say: str


ServerFrame = StateFrame | EmotionFrame | AudioFrame | FinalFrame
