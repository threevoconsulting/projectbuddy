"""Session lifecycle.

``/session/start`` returns the resume summary (medium-term memory) so Buddy can pick
up where the child left off; ``/session/end`` writes the new summary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from projectbuddy.deps import Container, get_container
from projectbuddy.protocol.rest import (
    MessageOut,
    SessionEndRequest,
    SessionEndResponse,
    SessionStartRequest,
    SessionStartResponse,
)

router = APIRouter(prefix="/session")


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    body: SessionStartRequest, c: Container = Depends(get_container)
) -> SessionStartResponse:
    if body.person_id is None:
        person = c.persons.get_or_create_default()
    else:
        found = c.persons.get(body.person_id)
        if found is None:
            raise HTTPException(status_code=404, detail="person not found")
        person = found

    resume = c.memory.resume_summary(person.id)
    session = c.sessions.start(person.id)
    c.persons.touch_last_seen(person.id)
    return SessionStartResponse(session_id=session.id, person_id=person.id, resume_summary=resume)


@router.post("/end", response_model=SessionEndResponse)
async def end_session(
    body: SessionEndRequest, c: Container = Depends(get_container)
) -> SessionEndResponse:
    session = c.sessions.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    summary = c.memory.summarize_session(session.id)
    c.sessions.end(session.id, summary)
    return SessionEndResponse(session_id=session.id, summary=summary)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def list_messages(session_id: int, c: Container = Depends(get_container)) -> list[MessageOut]:
    """Full transcript of a session (parent's Conversation screen)."""
    if c.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="session not found")
    return [
        MessageOut(id=m.id, role=m.role, text=m.text, emotion=m.emotion, created_at=m.created_at)
        for m in c.messages.list_by_session(session_id)
    ]
