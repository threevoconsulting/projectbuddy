"""Piper TTS adapter (real backend; runs on the household Mac).

Streams raw PCM from the Piper CLI: text in on stdin, 16-bit mono PCM out on stdout,
read in chunks and yielded as they arrive so playback can start before the whole line
is rendered. Piper is invoked as a subprocess (no Python import), so this module is
safe to import in CI; only ``run_mac.sh`` actually has the binary + a voice installed.

Pick a warm, friendly voice (TDD §5.3). Configure the binary and voice path via
settings; download voices with ``scripts/pull_models.sh``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

_READ_CHUNK = 4096


class PiperTTSEngine:
    def __init__(
        self,
        *,
        voice_path: str,
        binary: str = "piper",
    ) -> None:
        self._voice_path = voice_path
        self._binary = binary

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        proc = await asyncio.create_subprocess_exec(
            self._binary,
            "--model",
            self._voice_path,
            "--output_raw",  # raw PCM to stdout (no WAV header)
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(text.encode("utf-8"))
        proc.stdin.write_eof()
        try:
            while True:
                chunk = await proc.stdout.read(_READ_CHUNK)
                if not chunk:
                    break
                yield chunk
        finally:
            await proc.wait()
