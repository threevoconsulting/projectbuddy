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
from collections.abc import AsyncIterator

from projectbuddy.core import safety
from projectbuddy.core.output_parser import parse_reply
from projectbuddy.db.repositories import Person, SessionRow
from projectbuddy.deps import Container
from projectbuddy.protocol.ws import (
    AudioFrame,
    EmotionFrame,
    FinalFrame,
    ServerFrame,
    StateFrame,
)


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
    """Drive one turn from a transcript, yielding frames in protocol order."""
    yield StateFrame(value="thinking")

    messages = c.memory.build_context(
        person_id=person.id, session_id=session.id, child_text=transcript
    )
    raw = await c.llm.chat(messages, json=True)
    reply = await parse_reply(raw, messages, c.llm)
    reply = safety.enforce(reply)

    # Face leads the voice: emotion before any audio. The `speaking` state then
    # tells the client the reply is on its way (so the face leaves `thinking` even
    # before the first audio chunk arrives), while the emotion already set the mood.
    yield EmotionFrame(value=reply.emotion)
    yield StateFrame(value="speaking")
    async for chunk in c.tts.synthesize(reply.say):
        yield AudioFrame(chunk=base64.b64encode(chunk).decode("ascii"))

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
    raw = await c.llm.chat(messages, json=True)
    reply = await parse_reply(raw, messages, c.llm)
    reply = safety.enforce(reply)

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
