"""The fake TTS streams 16-bit PCM chunks sized to the text length."""

from __future__ import annotations

from projectbuddy.models.tts.base import SAMPLE_RATE
from projectbuddy.models.tts.fake import FakeTTSEngine


async def _collect(text: str) -> list[bytes]:
    return [chunk async for chunk in FakeTTSEngine().synthesize(text)]


async def test_streams_multiple_chunks() -> None:
    chunks = await _collect("A longer line gets more audio chunks than a short one.")
    assert len(chunks) > 1
    assert all(isinstance(c, bytes) and c for c in chunks)
    # 16-bit samples → every chunk is an even number of bytes.
    assert all(len(c) % 2 == 0 for c in chunks)


async def test_longer_text_yields_more_audio() -> None:
    short = b"".join(await _collect("hi"))
    long = b"".join(await _collect("hello " * 50))
    assert len(long) > len(short)


async def test_duration_is_bounded() -> None:
    # Even an empty line produces the minimum 0.3 s; a huge line caps at 8 s.
    min_bytes = len(b"".join(await _collect("")))
    assert min_bytes >= int(0.3 * SAMPLE_RATE) * 2 - 4  # ~0.3 s of 16-bit mono
    max_bytes = len(b"".join(await _collect("x" * 10000)))
    assert max_bytes <= int(8.0 * SAMPLE_RATE) * 2 + 4  # ≤ 8 s
