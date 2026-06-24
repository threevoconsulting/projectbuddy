from __future__ import annotations

from projectbuddy.db.engine import Database
from projectbuddy.db.repositories import FactRepo, MessageRepo, PersonRepo, SessionRepo


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
