"""Face recognition + parental consent (Phase 2a, M7).

The consent gate is the heart of this surface: Buddy will not enroll or store a face
embedding for a child until a parent has granted ``face`` consent (``POST
/person/{id}/consent``). Enrollment averages one or more capture frames into a single
embedding; recognition matches a probe against enrolled embeddings by cosine
similarity. Images arrive base64-encoded in JSON, are embedded **in memory, and are
never written to disk** — only the resulting vector is persisted.

Deleting a person (``DELETE /person/{id}``) cascades to their embedding and consent
rows, so "forget" still removes every trace.
"""

from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException

from projectbuddy.core.recognition import average_vectors, best_match
from projectbuddy.core.retention import sweep_face_retention
from projectbuddy.deps import Container, get_container
from projectbuddy.protocol.rest import (
    ConsentOut,
    ConsentSet,
    EnrollRequest,
    EnrollResponse,
    RecognizeRequest,
    RecognizeResponse,
    RetentionRunResponse,
)

router = APIRouter()

_FACE = "face"


def _decode(image_b64: str) -> bytes:
    try:
        return base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid base64 image") from exc


def _require_person(c: Container, person_id: int) -> None:
    if c.persons.get(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")


@router.post("/person/{person_id}/consent", response_model=ConsentOut)
async def set_consent(
    person_id: int, body: ConsentSet, c: Container = Depends(get_container)
) -> ConsentOut:
    _require_person(c, person_id)
    if body.granted:
        c.consents.grant(
            person_id,
            body.scope,
            granted_by=body.granted_by,
            retention_until=body.retention_until,
            notes=body.notes,
        )
    else:
        c.consents.revoke(person_id, body.scope)
        # Revoking face consent removes the stored face template immediately.
        if body.scope == _FACE:
            c.face_embeddings.delete(person_id)
    row = c.consents.get(person_id, body.scope)
    assert row is not None
    return ConsentOut(
        person_id=row.person_id,
        scope=row.scope,
        granted=row.granted,
        granted_at=row.granted_at,
        granted_by=row.granted_by,
        retention_until=row.retention_until,
    )


@router.get("/person/{person_id}/consent", response_model=list[ConsentOut])
async def list_consent(person_id: int, c: Container = Depends(get_container)) -> list[ConsentOut]:
    _require_person(c, person_id)
    return [
        ConsentOut(
            person_id=row.person_id,
            scope=row.scope,
            granted=row.granted,
            granted_at=row.granted_at,
            granted_by=row.granted_by,
            retention_until=row.retention_until,
        )
        for row in c.consents.list_by_person(person_id)
    ]


@router.post("/person/{person_id}/enroll", response_model=EnrollResponse)
async def enroll_face(
    person_id: int, body: EnrollRequest, c: Container = Depends(get_container)
) -> EnrollResponse:
    _require_person(c, person_id)
    if not c.consents.has_consent(person_id, _FACE):
        raise HTTPException(status_code=403, detail="face consent required")

    vectors: list[list[float]] = []
    for image_b64 in body.images:
        image = _decode(image_b64)
        if not await c.liveness.check(image):  # anti-spoof gate (no-op on the fake backend)
            raise HTTPException(status_code=400, detail="liveness check failed")
        vector = await c.recognition.embed(image)
        if vector is not None:
            vectors.append(vector)
    if not vectors:
        raise HTTPException(status_code=400, detail="no face detected")

    averaged = average_vectors(vectors)
    row = c.face_embeddings.upsert(person_id, averaged, frames=len(vectors))
    return EnrollResponse(person_id=person_id, frames=row.frames, vector_size=len(averaged))


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_face(
    body: RecognizeRequest, c: Container = Depends(get_container)
) -> RecognizeResponse:
    image = _decode(body.image)
    if not await c.liveness.check(image):  # spoof/empty → no face
        return RecognizeResponse(matched=False, confidence=0.0, face_present=False)
    probe = await c.recognition.embed(image)
    if probe is None:  # no face in the frame
        return RecognizeResponse(matched=False, confidence=0.0, face_present=False)
    enrolled = [(row.person_id, row.vector) for row in c.face_embeddings.list_all()]
    person_id, score = best_match(probe, enrolled, c.settings.recognition_match_threshold)
    display_name = None
    if person_id is not None:
        person = c.persons.get(person_id)
        display_name = person.display_name if person else None
    return RecognizeResponse(
        matched=person_id is not None,
        person_id=person_id,
        display_name=display_name,
        confidence=score,
        face_present=True,  # a face is here, even if we don't know whose
    )


@router.post("/retention/run", response_model=RetentionRunResponse)
async def run_retention(c: Container = Depends(get_container)) -> RetentionRunResponse:
    """Delete face data past its retention date now (also runs on a timer)."""
    deleted = sweep_face_retention(c.consents, c.face_embeddings)
    return RetentionRunResponse(deleted_person_ids=deleted)
