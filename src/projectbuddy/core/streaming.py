"""Turn a *streaming* LLM JSON envelope into the emotion + spoken sentences early.

The model emits ``{"emotion": "...", "say": "...", "remember": [...]}``. Waiting for
the whole object before speaking is the main latency. :class:`SentenceStreamer` watches
the growing text and surfaces (1) the ``emotion`` as soon as it appears (so the face can
lead) and (2) completed sentences of ``say`` as they form, so TTS can start at once. The
full raw is still kept for an authoritative final parse (memory + the final transcript).
"""

from __future__ import annotations

import re

_EMOTION_RE = re.compile(r'"emotion"\s*:\s*"([^"]+)"')
_SAY_OPEN_RE = re.compile(r'"say"\s*:\s*"')
_TERMINATORS = ".!?…"
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}


def _decode_say(raw: str, start: int) -> tuple[str, bool]:
    """Decode the JSON string value beginning at ``start`` (just after its opening quote).

    Returns ``(value_so_far, closed)`` — ``closed`` is True once the terminating quote
    has arrived. Handles standard JSON escapes; a dangling backslash means "wait".
    """
    out: list[str] = []
    i = start
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == "\\":
            if i + 1 >= n:
                break  # incomplete escape at the buffer edge — wait for more
            out.append(_ESCAPES.get(raw[i + 1], raw[i + 1]))
            i += 2
            continue
        if ch == '"':
            return "".join(out), True
        out.append(ch)
        i += 1
    return "".join(out), False


def _last_terminator(text: str) -> int:
    """Index just past the last sentence terminator in ``text`` (0 if none)."""
    best = -1
    for i, ch in enumerate(text):
        if ch in _TERMINATORS:
            best = i
    return best + 1 if best >= 0 else 0


class SentenceStreamer:
    def __init__(self) -> None:
        self.raw = ""
        self.emotion: str | None = None
        self._say_start: int | None = None
        self._spoken = 0  # chars of the say value already returned as sentences

    def feed(self, delta: str) -> tuple[str | None, str]:
        """Add a token delta. Returns (emotion_first_time_or_None, flushed_speech_or_'')."""
        self.raw += delta

        new_emotion = None
        if self.emotion is None:
            m = _EMOTION_RE.search(self.raw)
            if m and m.group(1).strip():
                self.emotion = m.group(1).strip().lower()
                new_emotion = self.emotion

        if self._say_start is None:
            m = _SAY_OPEN_RE.search(self.raw)
            if m:
                self._say_start = m.end()

        flushed = ""
        if self._say_start is not None:
            value, closed = _decode_say(self.raw, self._say_start)
            pending = value[self._spoken :]
            cut = len(pending) if closed else _last_terminator(pending)
            if cut > 0:
                flushed = pending[:cut]
                self._spoken += cut
        return new_emotion, flushed

    def say_value(self) -> str:
        """The full ``say`` text decoded so far (used to reconstruct the final reply)."""
        if self._say_start is None:
            return ""
        value, _ = _decode_say(self.raw, self._say_start)
        return value
