"""Deterministic fake TTS — powers CI, tests, and the no-models dev container.

It synthesizes a short, low-volume sine tone sized to the text length and streams it
in fixed-size chunks, so the WebSocket audio loop and the front-end mouth animation
have real bytes to carry without any model. No external dependencies.
"""

from __future__ import annotations

import math
from array import array
from collections.abc import AsyncIterator

from projectbuddy.models.tts.base import SAMPLE_RATE

_CHUNK_SECONDS = 0.1
_TONE_HZ = 180.0
_AMPLITUDE = 0.18  # gentle; this is a placeholder voice, not Buddy's real one


class FakeTTSEngine:
    def __init__(self, *, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        duration = min(8.0, max(0.3, len(text) * 0.06))
        per_chunk = int(self._sample_rate * _CHUNK_SECONDS)
        total = int(self._sample_rate * duration)
        peak = int(_AMPLITUDE * 32767)

        for start in range(0, total, per_chunk):
            count = min(per_chunk, total - start)
            samples = array("h", (0 for _ in range(count)))
            for i in range(count):
                n = start + i
                samples[i] = int(peak * math.sin(2 * math.pi * _TONE_HZ * n / self._sample_rate))
            yield samples.tobytes()
