"""People & long-term memory transparency (parent-facing).

``GET /person/{id}/facts`` is the COPPA access surface — it shows exactly what Buddy
remembers. ``DELETE /person/{id}`` is "forget", a single cascade delete.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from projectbuddy.deps import Container, get_container
from projectbuddy.protocol.rest import FactOut, PersonCreate, PersonOut

router = APIRouter(prefix="/person")


@router.get("", response_model=list[PersonOut])
async def list_people(c: Container = Depends(get_container)) -> list[PersonOut]:
    return [PersonOut(**p.__dict__) for p in c.persons.list()]


@router.post("", response_model=PersonOut, status_code=201)
async def create_person(body: PersonCreate, c: Container = Depends(get_container)) -> PersonOut:
    person = c.persons.create(body.display_name, body.role)
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
