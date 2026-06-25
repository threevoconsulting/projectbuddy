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
import logging

from fastapi import APIRouter, Depends, HTTPException

from projectbuddy.core.recognition import average_vectors, best_match, cosine
from projectbuddy.deps import Container, get_container
from projectbuddy.protocol.rest import (
    ConsentOut,
    ConsentSet,
    EnrollRequest,
    EnrollResponse,
    RecognizeRequest,
    RecognizeResponse,
)

router = APIRouter()

# Logs to uvicorn's configured logger so diagnostics show in the run-mac terminal.
_log = logging.getLogger("uvicorn.error")

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
        vector = await c.recognition.embed(_decode(image_b64))
        if vector is not None:
            vectors.append(vector)

    # Diagnostic: cosine between the different captured frames of the SAME face. ~0.6+
    # means the recognizer discriminates identity (good); ~0 means it does not.
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            _log.info("enroll cross-frame cosine[%d,%d] = %.4f", i, j, cosine(vectors[i], vectors[j]))
    _log.info("enroll person=%s faces=%d/%d", person_id, len(vectors), len(body.images))
    if not vectors:
        raise HTTPException(status_code=400, detail="no face detected")

    averaged = average_vectors(vectors)
    norm = sum(x * x for x in averaged) ** 0.5
    _log.info("enroll person=%s dim=%d norm=%.3f", person_id, len(averaged), norm)
    row = c.face_embeddings.upsert(person_id, averaged, frames=len(vectors))
    return EnrollResponse(person_id=person_id, frames=row.frames, vector_size=len(averaged))


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_face(
    body: RecognizeRequest, c: Container = Depends(get_container)
) -> RecognizeResponse:
    probe = await c.recognition.embed(_decode(body.image))
    if probe is None:
        _log.info("recognize: no face detected in probe frame")
        return RecognizeResponse(matched=False, person_id=None, confidence=0.0)
    enrolled = [(row.person_id, row.vector) for row in c.face_embeddings.list_all()]
    person_id, score = best_match(probe, enrolled, c.settings.recognition_match_threshold)
    _log.info(
        "recognize: enrolled=%d best_id=%s score=%.3f thr=%.2f",
        len(enrolled),
        person_id,
        score,
        c.settings.recognition_match_threshold,
    )
    return RecognizeResponse(matched=person_id is not None, person_id=person_id, confidence=score)
