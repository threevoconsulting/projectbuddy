"""The text-to-speech seam.

Buddy's voice is produced only through :class:`TTSEngine`. Synthesis is **streaming**:
``synthesize`` yields PCM byte chunks as they are produced so the face can start
playing (and the mouth start moving) before the whole line is rendered — part of the
≤2.0 s latency budget (TDD §NFR-1). The fake powers CI; Piper runs on the Mac.

Audio is raw 16-bit little-endian mono PCM at :data:`SAMPLE_RATE`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

SAMPLE_RATE = 22_050  # Hz, mono, 16-bit signed PCM (Piper's native rate)


class TTSEngine(Protocol):
    def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Yield PCM audio chunks for ``text`` as they are synthesized."""
        ...
