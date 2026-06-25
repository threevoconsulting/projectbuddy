"""Kokoro TTS adapter (real backend; optional, runs on the household Mac).

Kokoro is a small, modern neural TTS that sounds more lifelike than Piper. It's an
optional alternative voice: set ``PB_TTS_BACKEND=kokoro``. Heavy imports (``kokoro``,
``numpy``, and its torch dependency) are deferred to construction so importing this
module never breaks CI.

Kokoro renders at 24 kHz; we resample to the project's canonical 22.05 kHz so the
WebSocket audio contract and the front-end playback rate stay unchanged.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from projectbuddy.models.tts.base import SAMPLE_RATE

_KOKORO_RATE = 24_000


class KokoroTTSEngine:
    def __init__(self, *, voice: str = "af_heart", lang_code: str = "a") -> None:
        from kokoro import KPipeline  # lazy: optional Mac dependency

        self._pipeline = KPipeline(lang_code=lang_code)
        self._voice = voice

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        import numpy as np  # lazy: optional Mac dependency

        for _gs, _ps, audio in self._pipeline(text, voice=self._voice):
            samples = np.asarray(audio, dtype=np.float32)
            if _KOKORO_RATE != SAMPLE_RATE:
                samples = _resample(samples, _KOKORO_RATE, SAMPLE_RATE, np)
            pcm = np.clip(samples, -1.0, 1.0)
            yield (pcm * 32767).astype("<i2").tobytes()


def _resample(samples: object, src_rate: int, dst_rate: int, np: object) -> object:
    """Linear resample a 1-D float array — light, dependency-free, fine for speech."""
    n_src = samples.shape[0]  # type: ignore[attr-defined]
    n_dst = round(n_src * dst_rate / src_rate)
    if n_dst <= 0:
        return np.zeros(0, dtype="float32")  # type: ignore[attr-defined]
    src_idx = np.arange(n_src, dtype="float32")  # type: ignore[attr-defined]
    dst_idx = np.linspace(0, n_src - 1, n_dst, dtype="float32")  # type: ignore[attr-defined]
    return np.interp(dst_idx, src_idx, samples).astype("float32")  # type: ignore[attr-defined]
