#!/usr/bin/env python3
"""Synthesize the same Buddy lines through several voices so you can pick one.

Mac-only (needs the real TTS engines: `uv sync --extra mac`). Writes one WAV per
candidate to ./voice-samples/ — open them and listen. Nothing here runs in CI.

    uv run python scripts/compare_voices.py
    uv run python scripts/compare_voices.py --piper-dir ./models/piper

Each candidate is a (label, engine) pair; add or remove freely. Kokoro is included
only if it's installed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from projectbuddy.models.tts.base import SAMPLE_RATE

# A few lines that exercise warmth, excitement, and a gentle moment.
LINES = [
    "Hi! I'm Buddy. Want to hear a fun fact about dinosaurs?",
    "Wow, a rocket! They blast fire to zoom up super fast. Isn't that amazing?",
    "It's okay to feel sad sometimes. I'm right here with you.",
]


async def _render(engine: object, text: str) -> bytes:
    chunks = [chunk async for chunk in engine.synthesize(text)]  # type: ignore[attr-defined]
    return b"".join(chunks)


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(rate)
        wav.writeframes(pcm)


def _candidates(piper_dir: Path) -> list[tuple[str, object, int]]:
    """(label, engine, sample_rate). Skips engines that aren't installed/available."""
    out: list[tuple[str, object, int]] = []

    from projectbuddy.models.tts.piper import PiperTTSEngine

    for voice in ("en_US-lessac-high", "en_US-amy-medium"):
        onnx = piper_dir / f"{voice}.onnx"
        if onnx.exists():
            out.append((f"piper-{voice}", PiperTTSEngine(voice_path=str(onnx)), SAMPLE_RATE))
        else:
            print(f"  (skip {voice}: {onnx} not found — run scripts/pull_models.sh)")

    try:
        from projectbuddy.models.tts.kokoro import KokoroTTSEngine

        out.append(("kokoro-af_heart", KokoroTTSEngine(voice="af_heart"), SAMPLE_RATE))
    except Exception as exc:  # kokoro optional / not installed
        print(f"  (skip kokoro: {exc})")

    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--piper-dir", default="./models/piper", type=Path)
    parser.add_argument("--out", default="./voice-samples", type=Path)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    candidates = _candidates(args.piper_dir)
    if not candidates:
        print("No voices available. Run `uv sync --extra mac` and scripts/pull_models.sh.")
        return 1

    for label, engine, rate in candidates:
        # One combined clip per voice so they're easy to A/B back to back.
        pcm = b"".join([await _render(engine, line) for line in LINES])
        path = args.out / f"{label}.wav"
        _write_wav(path, pcm, rate)
        print(f"  wrote {path}  ({len(pcm) / 2 / rate:.1f}s)")

    print(f"\nDone. Listen to the clips in {args.out}/ and set PB_PIPER_VOICE_PATH (or")
    print("PB_TTS_BACKEND=kokoro) to your favourite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
