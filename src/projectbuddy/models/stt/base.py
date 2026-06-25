"""The speech-to-text seam.

The child's voice reaches Buddy only through :class:`STTEngine`. The fake adapter
powers CI and the cloud dev container; the faster-whisper adapter runs on the
household Mac. The WebSocket handler depends on this Protocol, never on a concrete
backend.

Audio is raw 16-bit little-endian mono PCM at :data:`SAMPLE_RATE`. For push-to-talk
(v1) the handler buffers a whole utterance and hands it over in one call; a streaming
/ VAD-endpointing engine can be added behind the same Protocol later.
"""

from __future__ import annotations

from typing import Protocol

SAMPLE_RATE = 16_000  # Hz, mono, 16-bit signed PCM — the contract for both ends


class STTEngine(Protocol):
    async def transcribe(self, audio: bytes) -> str:
        """Transcribe one utterance of PCM audio into text (may be empty)."""
        ...
