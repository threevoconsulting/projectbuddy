"""Deterministic fake STT — powers CI, tests, and the no-models dev container.

It has no audio model. To let tests drive the conversation loop with a chosen
utterance, it treats the incoming PCM buffer as UTF-8 text: the "audio" a test sends
*is* the transcript. Real PCM (non-UTF-8) falls back to a canned line. A fixed
``transcript`` or a ``scripted`` list can override this for finer control.
"""

from __future__ import annotations

_DEFAULT = "Tell me a story about space."


class FakeSTTEngine:
    def __init__(self, *, transcript: str | None = None, scripted: list[str] | None = None) -> None:
        self._transcript = transcript
        self._scripted = list(scripted or [])
        self.calls: list[bytes] = []

    async def transcribe(self, audio: bytes) -> str:
        self.calls.append(audio)
        if self._scripted:
            return self._scripted.pop(0)
        if self._transcript is not None:
            return self._transcript
        try:
            text = audio.decode("utf-8").strip()
        except UnicodeDecodeError:
            return _DEFAULT
        return text or _DEFAULT
