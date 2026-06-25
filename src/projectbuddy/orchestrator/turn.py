"""One conversational turn, as a stream of server frames.

``run_turn`` is the heart of the voice loop and reuses the exact orchestration the
text loop uses (memory → LLM → parser → safety → memory). It depends only on the
container's adapters, so it runs end-to-end on the fakes in CI.

The critical ordering rule — **the face leads the voice** — lives here: the
``emotion`` frame is emitted before the first ``audio`` chunk, so Buddy's expression
changes the instant it "decides" how to feel, while TTS is still synthesizing.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import AsyncIterator

from projectbuddy.core import safety
from projectbuddy.core.output_parser import lenient_parse, parse_reply
from projectbuddy.core.safety import SAFE_SUBSTITUTE
from projectbuddy.core.streaming import SentenceStreamer
from projectbuddy.core.text import for_speech
from projectbuddy.db.repositories import Person, SessionRow
from projectbuddy.deps import Container
from projectbuddy.models.llm.base import ChatMessage
from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion
from projectbuddy.protocol.ws import (
    AudioFrame,
    EmotionFrame,
    FinalFrame,
    ServerFrame,
    StateFrame,
)

_log = logging.getLogger("uvicorn.error")

# Spoken when the brain is too slow / errors / returns nothing — never crash a turn.
_BRAIN_HICCUP = BuddyReply(
    emotion=Emotion.confused,
    say="My brain went quiet for a second. Can you say that again?",
    remember=[],
)


async def safe_reply(c: Container, messages: list[ChatMessage]) -> BuddyReply:
    """LLM + parse + safety, but never raise: a slow/failed brain → a gentle fallback."""
    try:
        raw = await c.llm.chat(messages, json=True)
        reply = await parse_reply(raw, messages, c.llm)
    except Exception as exc:  # httpx timeout, connection error, etc.
        _log.warning("brain error, using fallback: %r", exc)
        reply = _BRAIN_HICCUP.model_copy(deep=True)
    return safety.enforce(reply)


def _coerce_emotion(name: str | None) -> Emotion:
    try:
        return Emotion(name) if name else Emotion.happy
    except ValueError:
        return Emotion.happy


def resolve_session(c: Container, session_id: int | None) -> tuple[Person, SessionRow] | None:
    """Resolve (or start) the session for a turn.

    Returns ``None`` if a given ``session_id`` (or its person) no longer exists, so
    the caller can reject it; with no ``session_id`` a default person + new session
    are created (Phase 1 single-profile behaviour).
    """
    if session_id is None:
        default = c.persons.get_or_create_default()
        return default, c.sessions.start(default.id)

    session = c.sessions.get(session_id)
    if session is None:
        return None
    person = c.persons.get(session.person_id)
    if person is None:
        return None
    return person, session


async def run_turn(
    c: Container, *, person: Person, session: SessionRow, transcript: str
) -> AsyncIterator[ServerFrame]:
    """Drive one turn, streaming the brain so Buddy starts speaking the first sentence
    while the rest is still being generated (lower time-to-first-sound).

    Order is unchanged (the face still leads): thinking → emotion → speaking → audio… →
    final. Each sentence is safety-checked and emoji-stripped before it is spoken; the
    full envelope is parsed at the end for memory + the final transcript. Any streaming
    error falls back to the non-streaming :func:`safe_reply` path.
    """
    yield StateFrame(value="thinking")
    messages = c.memory.build_context(
        person_id=person.id, session_id=session.id, child_text=transcript
    )

    streamer = SentenceStreamer()
    emotion_sent = False
    speaking_sent = False
    spoke_any = False
    blocked = False

    try:
        async for delta in c.llm.chat_stream(messages, json=True):
            emo, flushed = streamer.feed(delta)
            if emo and not emotion_sent:
                emotion_sent = True
                yield EmotionFrame(value=_coerce_emotion(emo))
            if not flushed or blocked:
                continue
            if safety.check(flushed).blocked:
                blocked = True
                spoken = SAFE_SUBSTITUTE.say  # speak a safe line instead of the bad one
            else:
                spoken = for_speech(flushed)
            if spoken:
                if not emotion_sent:
                    emotion_sent = True
                    yield EmotionFrame(value=Emotion.happy)  # face leads even if emotion is late
                if not speaking_sent:
                    speaking_sent = True
                    yield StateFrame(value="speaking")
                async for chunk in c.tts.synthesize(spoken):
                    yield AudioFrame(chunk=base64.b64encode(chunk).decode("ascii"))
                spoke_any = True
            if blocked:
                break
    except Exception as exc:  # streaming/transport error → fall back below
        _log.warning("stream error, falling back: %r", exc)

    # Authoritative reply for memory + final transcript.
    if blocked:
        reply = SAFE_SUBSTITUTE.model_copy(deep=True)
    else:
        parsed = lenient_parse(streamer.raw) if streamer.raw.strip() else None
        if parsed is not None:
            reply = safety.enforce(parsed)
        else:
            say_value = streamer.say_value().strip()
            if say_value:
                reply = safety.enforce(
                    BuddyReply(emotion=_coerce_emotion(streamer.emotion), say=say_value)
                )
            else:
                reply = await safe_reply(c, messages)  # stream gave nothing usable

    if not spoke_any:
        # Nothing was streamed/spoken — speak the fallback reply now.
        if not emotion_sent:
            emotion_sent = True
            yield EmotionFrame(value=reply.emotion)
        if not speaking_sent:
            yield StateFrame(value="speaking")
        async for chunk in c.tts.synthesize(reply.say):
            yield AudioFrame(chunk=base64.b64encode(chunk).decode("ascii"))
    elif not emotion_sent:  # safety net — should not happen
        yield EmotionFrame(value=reply.emotion)

    yield FinalFrame(transcript=transcript, say=reply.say)

    c.memory.commit_turn(
        person_id=person.id, session_id=session.id, child_text=transcript, reply=reply
    )
    c.persons.touch_last_seen(person.id)


async def run_greeting(
    c: Container, *, person: Person, session: SessionRow, display_name: str | None = None
) -> AsyncIterator[ServerFrame]:
    """Greet a just-recognized person out loud (M8 continuity).

    Same pipeline as :func:`run_turn` but seeded by "the child arrived" instead of a
    spoken transcript, so Buddy welcomes them by name using what it remembers. Only
    Buddy's line is persisted (there is no child utterance).
    """
    yield StateFrame(value="thinking")

    messages = c.memory.build_greeting_context(
        person_id=person.id,
        session_id=session.id,
        display_name=display_name or person.display_name,
        role=person.role,
    )
    reply = await safe_reply(c, messages)

    yield EmotionFrame(value=reply.emotion)
    yield StateFrame(value="speaking")
    async for chunk in c.tts.synthesize(reply.say):
        yield AudioFrame(chunk=base64.b64encode(chunk).decode("ascii"))

    yield FinalFrame(transcript="", say=reply.say)

    c.memory.commit_buddy_line(session_id=session.id, reply=reply)
    c.persons.touch_last_seen(person.id)


# Buddy's first line to a face it doesn't recognize. Fixed (no LLM): fast, always
# child-safe, and consistent — the camera flow plays it when a new person appears.
INTRO_LINE = "Hi! My name is Buddy. What's your name?"


async def run_intro(c: Container) -> AsyncIterator[ServerFrame]:
    """Greet an unrecognized new face with a fixed, friendly introduction."""
    from projectbuddy.protocol.llm_envelope import Emotion

    yield EmotionFrame(value=Emotion.happy)
    yield StateFrame(value="speaking")
    async for chunk in c.tts.synthesize(INTRO_LINE):
        yield AudioFrame(chunk=base64.b64encode(chunk).decode("ascii"))
    yield FinalFrame(transcript="", say=INTRO_LINE)
