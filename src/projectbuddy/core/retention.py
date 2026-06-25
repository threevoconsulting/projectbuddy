"""Retention enforcement (M8 privacy).

Face data is biometric, so it should not outlive its consent. ``consent.retention_until``
sets an expiry; this sweep removes the face embedding and revokes the consent for any
person whose face consent has passed that date. It runs at startup, periodically, and
on demand (``POST /retention/run``). Chat memory (facts/sessions) is left untouched —
deleting a whole person is the separate ``DELETE /person/{id}`` cascade.
"""

from __future__ import annotations

from projectbuddy.db.repositories import ConsentRepo, FaceEmbeddingRepo


def sweep_face_retention(consents: ConsentRepo, face_embeddings: FaceEmbeddingRepo) -> list[int]:
    """Delete expired face embeddings and revoke their consent. Returns the person ids."""
    expired = consents.expired("face")
    for person_id in expired:
        face_embeddings.delete(person_id)
        consents.revoke(person_id, "face")
    return expired
