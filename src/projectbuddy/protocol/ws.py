"""WebSocket frame models for ``/ws/converse``.

Client → server (push-to-talk): an optional ``start`` to begin/continue a session,
then ``audio`` chunks while the mic is open, then ``end`` to close the utterance and
trigger a turn::

    {"type": "start", "session_id": 7}           # optional; omit for a new session
    {"type": "audio", "chunk": "<base64 pcm>"}    # 16 kHz mono 16-bit PCM
    ...
    {"type": "end"}

Server → client during one turn, in this order (the face leads the voice)::

    {"type": "state",   "value": "listening"}
    {"type": "state",   "value": "thinking"}
    {"type": "emotion", "value": "excited"}      # face animates now
    {"type": "audio",   "chunk": "<base64 pcm>"} # TTS streams; mouth animates
    ...
    {"type": "final",   "transcript": "...", "say": "..."}

The server frames were defined in M2 so the contract was stable and testable before
the audio pipeline landed; the client frames and handler arrived in M4.
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


# --- Client → server frames ---
class StartFrame(BaseModel):
    type: Literal["start"] = "start"
    session_id: int | None = None


class HelloFrame(BaseModel):
    """Ask Buddy to greet a just-recognized person (M8). Streams a greeting turn."""

    type: Literal["hello"] = "hello"
    session_id: int | None = None


class ClientAudioFrame(BaseModel):
    type: Literal["audio"] = "audio"
    chunk: str  # base64-encoded 16 kHz mono 16-bit PCM


class EndFrame(BaseModel):
    type: Literal["end"] = "end"


ClientFrame = StartFrame | HelloFrame | ClientAudioFrame | EndFrame
