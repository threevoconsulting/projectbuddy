"""The realtime voice loop — ``WS /ws/converse`` (M4).

Push-to-talk protocol: the client streams ``audio`` chunks while the mic is open,
then sends ``end``; the server transcribes the buffered utterance (STT), runs one
turn (:func:`orchestrator.turn.run_turn`), and streams ``state → emotion → audio →
final`` back. After each turn it returns to ``listening`` for the next utterance.

Empty/unintelligible input is handled gently (TDD §NFR-3) without bothering the LLM.
"""

from __future__ import annotations

import base64
import binascii
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from projectbuddy.deps import Container
from projectbuddy.orchestrator.turn import resolve_session, run_greeting, run_intro, run_turn
from projectbuddy.protocol.llm_envelope import Emotion
from projectbuddy.protocol.ws import (
    ClientAudioFrame,
    EndFrame,
    FinalFrame,
    HelloFrame,
    IntroFrame,
    StartFrame,
    StateFrame,
)

router = APIRouter()

# Logs to uvicorn's configured logger so voice diagnostics show in the run-mac terminal.
_log = logging.getLogger("uvicorn.error")

_DIDNT_CATCH = "Hmm, I didn't catch that. Can you say it again?"


@router.websocket("/ws/converse")
async def ws_converse(ws: WebSocket) -> None:
    container = ws.app.state.container
    assert isinstance(container, Container)

    await ws.accept()
    session_id: int | None = None
    buffer = bytearray()

    await ws.send_json(StateFrame(value="listening").model_dump())
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")

            if kind == "start":
                start = StartFrame.model_validate(msg)
                session_id = start.session_id
                buffer.clear()
                await ws.send_json(StateFrame(value="listening").model_dump())

            elif kind == "hello":
                # The camera recognized someone — greet them out loud (M8).
                hello = HelloFrame.model_validate(msg)
                session_id = await _handle_greeting(ws, container, hello.session_id)
                await ws.send_json(StateFrame(value="listening").model_dump())

            elif kind == "intro":
                # The camera sees an unrecognized new face — Buddy introduces itself.
                IntroFrame.model_validate(msg)
                async for out in run_intro(container):
                    await ws.send_json(out.model_dump())
                await ws.send_json(StateFrame(value="listening").model_dump())

            elif kind == "audio":
                try:
                    frame = ClientAudioFrame.model_validate(msg)
                    buffer.extend(base64.b64decode(frame.chunk, validate=True))
                except (ValidationError, binascii.Error):
                    continue  # ignore a malformed chunk; keep the mic open

            elif kind == "end":
                EndFrame.model_validate(msg)
                # Remember the resolved session so the next utterance on this
                # connection continues the same conversation.
                session_id = await _handle_utterance(ws, container, session_id, bytes(buffer))
                buffer.clear()
                await ws.send_json(StateFrame(value="listening").model_dump())
    except WebSocketDisconnect:
        return


async def _handle_utterance(
    ws: WebSocket, c: Container, session_id: int | None, audio: bytes
) -> int | None:
    """Transcribe + run one turn. Returns the session id to keep using."""
    # ~16 kHz mono 16-bit PCM → seconds = bytes / 2 / 16000.
    secs = len(audio) / 2 / 16000
    # A stray tap with no audio shouldn't create a session — answer gently and wait.
    if not audio:
        _log.info("voice: empty utterance (no audio captured)")
        await _didnt_catch(ws)
        return session_id

    resolved = resolve_session(c, session_id)
    if resolved is None:
        await ws.send_json(FinalFrame(transcript="", say="Let's start a new chat!").model_dump())
        return None  # drop the stale id; the next utterance starts fresh
    person, session = resolved

    transcript = (await c.stt.transcribe(audio)).strip()
    if not transcript:
        _log.info("voice: %.1fs audio -> STT heard nothing", secs)
        await _didnt_catch(ws)
        return session.id
    _log.info("voice: %.1fs audio -> heard: %r", secs, transcript)

    say = ""
    async for frame in run_turn(c, person=person, session=session, transcript=transcript):
        if isinstance(frame, FinalFrame):
            say = frame.say
        await ws.send_json(frame.model_dump())
    _log.info("voice: Buddy replied: %r", say)
    return session.id


async def _handle_greeting(ws: WebSocket, c: Container, session_id: int | None) -> int | None:
    """Run an arrival greeting for the recognized session. Returns the session id."""
    resolved = resolve_session(c, session_id)
    if resolved is None:
        return None
    person, session = resolved
    async for frame in run_greeting(c, person=person, session=session):
        await ws.send_json(frame.model_dump())
    return session.id


async def _didnt_catch(ws: WebSocket) -> None:
    """Gently ask the child to repeat (TDD §NFR-3) — confused face, no LLM turn."""
    await ws.send_json({"type": "emotion", "value": Emotion.confused.value})
    await ws.send_json(FinalFrame(transcript="", say=_DIDNT_CATCH).model_dump())
