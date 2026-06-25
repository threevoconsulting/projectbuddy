"""Real-model smoke tests for the latency budget (NFR-1) and TTS streaming.

Deselected in CI (`-m 'not smoke_mac'`); run on a Mac with the real stack:

    PB_LLM_BACKEND=ollama PB_STT_BACKEND=faster_whisper PB_TTS_BACKEND=piper \
    PB_PIPER_VOICE_PATH=./models/piper/en_US-lessac-high.onnx \
    uv run pytest -m smoke_mac -s

They assert, on real models:
  * the LLM emits a parseable envelope and the turn reaches first audio quickly,
  * the face leads the voice (emotion before the first audio chunk),
  * TTS actually streams (more than one audio chunk),
  * STT transcribes a short clip within budget (when audio fixtures are present).

The ≤2.0 s end-to-end target (TDD §NFR-1) splits as STT ≤400 ms, LLM first token
≤700 ms, TTS first audio ≤500 ms, overhead ≤400 ms. Here we bound the non-STT chain
(transcript → first audio) at 1.6 s and leave STT to its own check.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from projectbuddy.config import Settings
from projectbuddy.deps import Container
from projectbuddy.orchestrator.turn import resolve_session, run_turn

pytestmark = pytest.mark.smoke_mac

_TRANSCRIPT_TO_FIRST_AUDIO_BUDGET = 1.6  # seconds (LLM first token + TTS first audio + overhead)
_CLIP = Path(__file__).resolve().parents[1] / "fixtures" / "audio" / "dinosaurs_16k.pcm"


def _real_container() -> Container:
    settings = Settings()  # reads PB_* from the environment
    if settings.llm_backend == "fake" or settings.tts_backend == "fake":
        pytest.skip("set PB_LLM_BACKEND/PB_TTS_BACKEND to real backends for smoke tests")
    return Container.build(settings)


def _load_clip() -> bytes | None:
    """Sync file IO kept out of the async test (avoids blocking the loop)."""
    return _CLIP.read_bytes() if _CLIP.exists() else None


async def test_turn_first_audio_within_budget_and_streams() -> None:
    c = _real_container()
    try:
        await c.llm.warmup()  # pre-warm so the first real token isn't a cold start
        resolved = resolve_session(c, None)
        assert resolved is not None
        person, session = resolved

        start = time.monotonic()
        first_audio_at: float | None = None
        order: list[str] = []
        audio_chunks = 0

        async for frame in run_turn(
            c, person=person, session=session, transcript="Tell me a fun fact about dinosaurs."
        ):
            order.append(frame.type)
            if frame.type == "audio":
                audio_chunks += 1
                if first_audio_at is None:
                    first_audio_at = time.monotonic() - start

        assert first_audio_at is not None, "no audio was produced"
        assert first_audio_at <= _TRANSCRIPT_TO_FIRST_AUDIO_BUDGET, (
            f"first audio took {first_audio_at:.2f}s (budget {_TRANSCRIPT_TO_FIRST_AUDIO_BUDGET}s)"
        )
        # Face leads the voice, and TTS streams in multiple chunks.
        assert order.index("emotion") < order.index("audio")
        assert audio_chunks > 1, "TTS did not stream (expected multiple audio chunks)"
    finally:
        c.db.close()


async def test_stt_transcribes_short_clip_within_budget() -> None:
    c = _real_container()
    if c.settings.stt_backend == "fake":
        pytest.skip("set PB_STT_BACKEND=faster_whisper for the STT smoke test")
    try:
        clip = _load_clip()
        if clip is None:
            pytest.skip(f"record a 16 kHz mono PCM clip at {_CLIP} to run this check")

        start = time.monotonic()
        text = await c.stt.transcribe(clip)
        elapsed = time.monotonic() - start

        assert text.strip(), "STT returned an empty transcript"
        assert elapsed <= 1.5, f"STT took {elapsed:.2f}s for a short clip"
    finally:
        c.db.close()
