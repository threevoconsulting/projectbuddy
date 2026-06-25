"""faster-whisper STT adapter (real backend; runs on the household Mac).

Transcribes 16 kHz mono 16-bit PCM. Heavy imports (``faster_whisper``, ``numpy``)
are deferred to construction/first use so importing this module never breaks CI,
where the ``mac`` extra is not installed.

Child speech is harder than adult speech: expose model size and VAD as tunables and
keep a push-to-talk fallback in the UI (TDD §5.3).
"""

from __future__ import annotations


class FasterWhisperSTTEngine:
    def __init__(
        self,
        *,
        model: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        vad_filter: bool = True,
    ) -> None:
        from faster_whisper import WhisperModel  # lazy: Mac-only dependency

        self._model = WhisperModel(model, device=device, compute_type=compute_type)
        self._language = language
        self._vad_filter = vad_filter

    async def transcribe(self, audio: bytes) -> str:
        import numpy as np  # lazy: Mac-only dependency

        if not audio:
            return ""
        # 16-bit signed PCM → float32 in [-1, 1], as faster-whisper expects.
        samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(
            samples,
            language=self._language,
            vad_filter=self._vad_filter,
        )
        return " ".join(seg.text for seg in segments).strip()
