"""People & long-term memory transparency (parent-facing).

``GET /person/{id}/facts`` is the COPPA access surface — it shows exactly what Buddy
remembers. ``DELETE /person/{id}`` is "forget", a single cascade delete.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from projectbuddy.deps import Container, get_container
from projectbuddy.protocol.rest import (
    FactOut,
    PersonCreate,
    PersonOut,
    PersonStatsOut,
    PersonUpdate,
    SessionOut,
)

router = APIRouter(prefix="/person")


@router.get("", response_model=list[PersonOut])
async def list_people(c: Container = Depends(get_container)) -> list[PersonOut]:
    return [PersonOut(**p.__dict__) for p in c.persons.list()]


@router.post("", response_model=PersonOut, status_code=201)
async def create_person(body: PersonCreate, c: Container = Depends(get_container)) -> PersonOut:
    person = c.persons.create(body.display_name, body.role)
    return PersonOut(**person.__dict__)


@router.put("/{person_id}", response_model=PersonOut)
async def update_person(
    person_id: int, body: PersonUpdate, c: Container = Depends(get_container)
) -> PersonOut:
    person = c.persons.update(person_id, body.display_name, body.role)
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    return PersonOut(**person.__dict__)


@router.delete("/{person_id}", status_code=204)
async def forget_person(person_id: int, c: Container = Depends(get_container)) -> Response:
    if not c.persons.delete(person_id):
        raise HTTPException(status_code=404, detail="person not found")
    return Response(status_code=204)


@router.get("/{person_id}/facts", response_model=list[FactOut])
async def list_facts(person_id: int, c: Container = Depends(get_container)) -> list[FactOut]:
    if c.persons.get(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")
    return [FactOut(**f.__dict__) for f in c.facts.list(person_id)]


@router.delete("/{person_id}/facts/{fact_id}", status_code=204)
async def forget_fact(
    person_id: int, fact_id: int, c: Container = Depends(get_container)
) -> Response:
    """Delete one remembered fact (parent's Memory screen)."""
    if c.persons.get(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")
    if not c.facts.delete(fact_id):
        raise HTTPException(status_code=404, detail="fact not found")
    return Response(status_code=204)


@router.get("/{person_id}/sessions", response_model=list[SessionOut])
async def list_sessions(person_id: int, c: Container = Depends(get_container)) -> list[SessionOut]:
    if c.persons.get(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")
    return [
        SessionOut(id=s.id, started_at=s.started_at, ended_at=s.ended_at, summary=s.summary)
        for s in c.sessions.list_by_person(person_id)
    ]


@router.get("/{person_id}/stats", response_model=PersonStatsOut)
async def person_stats(person_id: int, c: Container = Depends(get_container)) -> PersonStatsOut:
    person = c.persons.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    return PersonStatsOut(
        person_id=person_id,
        session_count=c.sessions.count_by_person(person_id),
        message_count=c.messages.count_for_person(person_id),
        fact_count=len(c.facts.list(person_id)),
        created_at=person.created_at,
        last_seen_at=person.last_seen_at,
        face_enrolled=c.face_embeddings.get(person_id) is not None,
        face_consent=c.consents.has_consent(person_id, "face"),
    )
