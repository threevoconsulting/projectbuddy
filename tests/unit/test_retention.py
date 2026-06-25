"""Retention sweep: face data past its consent retention date is removed (M8)."""

from __future__ import annotations

from projectbuddy.core.retention import sweep_face_retention
from projectbuddy.db.engine import Database
from projectbuddy.db.repositories import ConsentRepo, FaceEmbeddingRepo, PersonRepo


def test_sweep_deletes_expired_face_data(db: Database) -> None:
    persons, consents, embeddings = PersonRepo(db), ConsentRepo(db), FaceEmbeddingRepo(db)
    p = persons.create("Emma")
    embeddings.upsert(p.id, [0.1, 0.2, 0.3])
    consents.grant(p.id, "face", retention_until="2000-01-01")  # already past

    deleted = sweep_face_retention(consents, embeddings)

    assert deleted == [p.id]
    assert embeddings.get(p.id) is None  # template removed
    assert consents.has_consent(p.id, "face") is False  # consent revoked


def test_sweep_keeps_unexpired_or_indefinite(db: Database) -> None:
    persons, consents, embeddings = PersonRepo(db), ConsentRepo(db), FaceEmbeddingRepo(db)
    future = persons.create("Ada")
    forever = persons.create("Grace")
    embeddings.upsert(future.id, [0.1])
    embeddings.upsert(forever.id, [0.2])
    consents.grant(future.id, "face", retention_until="2999-01-01")  # not yet
    consents.grant(forever.id, "face")  # retention_until = NULL -> keep

    assert sweep_face_retention(consents, embeddings) == []
    assert embeddings.get(future.id) is not None
    assert embeddings.get(forever.id) is not None
