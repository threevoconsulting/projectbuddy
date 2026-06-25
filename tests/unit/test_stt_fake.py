"""The fake STT decodes a test's bytes as the transcript, with sensible fallbacks."""

from __future__ import annotations

from projectbuddy.models.stt.fake import FakeSTTEngine


async def test_treats_utf8_bytes_as_transcript() -> None:
    stt = FakeSTTEngine()
    assert await stt.transcribe(b"I love dinosaurs!") == "I love dinosaurs!"


async def test_non_utf8_falls_back_to_canned_line() -> None:
    stt = FakeSTTEngine()
    out = await stt.transcribe(b"\xff\xfe\x00\x01")  # not valid UTF-8 (real PCM-ish)
    assert out  # never empty


async def test_empty_audio_falls_back() -> None:
    stt = FakeSTTEngine()
    assert await stt.transcribe(b"") == "Tell me a story about space."


async def test_fixed_and_scripted_overrides() -> None:
    fixed = FakeSTTEngine(transcript="hello buddy")
    assert await fixed.transcribe(b"ignored") == "hello buddy"

    scripted = FakeSTTEngine(scripted=["first", "second"])
    assert await scripted.transcribe(b"") == "first"
    assert await scripted.transcribe(b"") == "second"
    assert scripted.calls == [b"", b""]
