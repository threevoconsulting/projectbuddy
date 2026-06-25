from __future__ import annotations

from projectbuddy.db.engine import Database
from projectbuddy.db.repositories import (
    ConsentRepo,
    FaceEmbeddingRepo,
    FactRepo,
    MessageRepo,
    PersonRepo,
    SessionRepo,
)


def test_person_crud(db: Database) -> None:
    persons = PersonRepo(db)
    p = persons.create("Emma", role="child")
    assert p.id > 0
    assert persons.get(p.id) is not None
    assert [x.id for x in persons.list()] == [p.id]


def test_fact_upsert_dedups_by_key(db: Database) -> None:
    persons, facts = PersonRepo(db), FactRepo(db)
    p = persons.create("Emma")
    facts.upsert(p.id, "favorite_dino", "stegosaurus")
    facts.upsert(p.id, "favorite_dino", "trex")  # same key -> update, not duplicate
    rows = facts.list(p.id)
    assert len(rows) == 1
    assert rows[0].value == "trex"


def test_delete_person_cascades(db: Database) -> None:
    persons = PersonRepo(db)
    facts = FactRepo(db)
    sessions = SessionRepo(db)
    messages = MessageRepo(db)

    p = persons.create("Emma")
    facts.upsert(p.id, "color", "teal")
    s = sessions.start(p.id)
    messages.add(s.id, "child", "hi")
    messages.add(s.id, "buddy", "hello!", emotion="happy")

    assert persons.delete(p.id) is True

    # Everything for the person is gone — no orphan rows.
    assert persons.get(p.id) is None
    assert facts.list(p.id) == []
    assert sessions.get(s.id) is None
    assert messages.recent(s.id, 10) == []


def test_session_summary_resume(db: Database) -> None:
    persons, sessions = PersonRepo(db), SessionRepo(db)
    p = persons.create("Emma")
    s = sessions.start(p.id)
    sessions.end(s.id, "We talked about rockets")
    assert sessions.latest_summary(p.id) == "We talked about rockets"


def test_message_recent_returns_chronological_tail(db: Database) -> None:
    persons, sessions, messages = PersonRepo(db), SessionRepo(db), MessageRepo(db)
    p = persons.create("Emma")
    s = sessions.start(p.id)
    for i in range(5):
        messages.add(s.id, "child", f"msg{i}")
    recent = messages.recent(s.id, 3)
    assert [m.text for m in recent] == ["msg2", "msg3", "msg4"]


# --- M7: face embeddings + consent ---
def test_face_embedding_upsert_roundtrips_and_dedupes(db: Database) -> None:
    persons, embeddings = PersonRepo(db), FaceEmbeddingRepo(db)
    p = persons.create("Emma")
    embeddings.upsert(p.id, [0.1, 0.2, 0.3], frames=3)
    embeddings.upsert(p.id, [0.4, 0.5, 0.6], frames=5)  # one row per person → update
    rows = embeddings.list_all()
    assert len(rows) == 1
    assert rows[0].vector == [0.4, 0.5, 0.6]  # JSON round-trips the floats
    assert rows[0].frames == 5


def test_consent_grant_and_revoke(db: Database) -> None:
    persons, consents = PersonRepo(db), ConsentRepo(db)
    p = persons.create("Emma")
    assert consents.has_consent(p.id, "face") is False
    consents.grant(p.id, "face", granted_by="parent@example.com")
    assert consents.has_consent(p.id, "face") is True
    row = consents.get(p.id, "face")
    assert row is not None and row.granted_by == "parent@example.com"
    consents.revoke(p.id, "face")
    assert consents.has_consent(p.id, "face") is False
    # Revoke keeps an auditable row rather than deleting it.
    assert consents.get(p.id, "face") is not None


def test_delete_person_cascades_to_face_and_consent(db: Database) -> None:
    persons = PersonRepo(db)
    embeddings = FaceEmbeddingRepo(db)
    consents = ConsentRepo(db)

    p = persons.create("Emma")
    embeddings.upsert(p.id, [0.1, 0.2])
    consents.grant(p.id, "face", granted_by="parent@example.com")

    assert persons.delete(p.id) is True

    # "Forget" removes the face embedding and consent too — no orphan rows.
    assert embeddings.get(p.id) is None
    assert consents.get(p.id, "face") is None
