"""The text-only conversation loop (M1/M3).

``POST /converse-text`` is the brain without the voice: child text in, a validated,
safety-checked Buddy reply out (emotion + say + remembered facts), with full memory.
The M4 ``/ws/converse`` audio loop reuses the same orchestration.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from projectbuddy.core import safety
from projectbuddy.core.output_parser import parse_reply
from projectbuddy.db.repositories import Person, SessionRow
from projectbuddy.deps import Container, get_container
from projectbuddy.protocol.rest import ConverseTextRequest, ConverseTextResponse

router = APIRouter()


@router.post("/converse-text", response_model=ConverseTextResponse)
async def converse_text(
    req: ConverseTextRequest, c: Container = Depends(get_container)
) -> ConverseTextResponse:
    person: Person
    session: SessionRow
    if req.session_id is None:
        person = c.persons.get_or_create_default()
        session = c.sessions.start(person.id)
    else:
        found_session = c.sessions.get(req.session_id)
        if found_session is None:
            raise HTTPException(status_code=404, detail="session not found")
        found_person = c.persons.get(found_session.person_id)
        if found_person is None:
            raise HTTPException(status_code=404, detail="person not found")
        session, person = found_session, found_person

    messages = c.memory.build_context(
        person_id=person.id, session_id=session.id, child_text=req.text
    )
    raw = await c.llm.chat(messages, json=True)
    reply = await parse_reply(raw, messages, c.llm)
    reply = safety.enforce(reply)

    c.memory.commit_turn(
        person_id=person.id, session_id=session.id, child_text=req.text, reply=reply
    )
    c.persons.touch_last_seen(person.id)
    return ConverseTextResponse(reply=reply, session_id=session.id)
