"""Typed repositories — the only place that touches SQL.

Keeping persistence behind small repos makes the data layer easy to read, easy to
test on an in-memory DB, and keeps the cascade-delete behaviour ("forget this
person") in one obvious spot.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from projectbuddy.db.engine import Database


@dataclass(frozen=True)
class Person:
    id: int
    display_name: str
    role: str | None
    created_at: str
    last_seen_at: str | None


@dataclass(frozen=True)
class FactRow:
    id: int
    key: str
    value: str
    confidence: float
    updated_at: str


@dataclass(frozen=True)
class SessionRow:
    id: int
    person_id: int
    started_at: str
    ended_at: str | None
    summary: str | None


@dataclass(frozen=True)
class MessageRow:
    id: int
    session_id: int
    role: str
    text: str
    emotion: str | None
    created_at: str


class PersonRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, display_name: str, role: str | None = None) -> Person:
        cur = self._db.execute(
            "INSERT INTO person(display_name, role) VALUES (?, ?)", (display_name, role)
        )
        assert cur.lastrowid is not None
        person = self.get(cur.lastrowid)
        assert person is not None
        return person

    def get(self, person_id: int) -> Person | None:
        row = self._db.query_one("SELECT * FROM person WHERE id = ?", (person_id,))
        return _to_person(row) if row else None

    def list(self) -> list[Person]:
        rows = self._db.query_all("SELECT * FROM person ORDER BY id")
        return [_to_person(r) for r in rows]

    def touch_last_seen(self, person_id: int) -> None:
        self._db.execute(
            "UPDATE person SET last_seen_at = datetime('now') WHERE id = ?", (person_id,)
        )

    def delete(self, person_id: int) -> bool:
        """Forget a person: cascades to their facts, sessions, and messages."""
        cur = self._db.execute("DELETE FROM person WHERE id = ?", (person_id,))
        return cur.rowcount > 0

    def get_or_create_default(self) -> Person:
        """Phase 1 single-profile convenience."""
        row = self._db.query_one("SELECT * FROM person ORDER BY id LIMIT 1")
        if row:
            return _to_person(row)
        return self.create("Buddy's friend", role="child")


class FactRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert(self, person_id: int, key: str, value: str, confidence: float = 1.0) -> None:
        self._db.execute(
            "INSERT INTO fact(person_id, key, value, confidence) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(person_id, key) DO UPDATE SET "
            "value = excluded.value, confidence = excluded.confidence, "
            "updated_at = datetime('now')",
            (person_id, key, value, confidence),
        )

    def list(self, person_id: int) -> list[FactRow]:
        rows = self._db.query_all(
            "SELECT * FROM fact WHERE person_id = ? ORDER BY updated_at DESC", (person_id,)
        )
        return [_to_fact(r) for r in rows]

    def delete(self, fact_id: int) -> bool:
        cur = self._db.execute("DELETE FROM fact WHERE id = ?", (fact_id,))
        return cur.rowcount > 0


class SessionRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def start(self, person_id: int) -> SessionRow:
        cur = self._db.execute("INSERT INTO session(person_id) VALUES (?)", (person_id,))
        assert cur.lastrowid is not None
        row = self.get(cur.lastrowid)
        assert row is not None
        return row

    def get(self, session_id: int) -> SessionRow | None:
        row = self._db.query_one("SELECT * FROM session WHERE id = ?", (session_id,))
        return _to_session(row) if row else None

    def latest_summary(self, person_id: int) -> str | None:
        row = self._db.query_one(
            "SELECT summary FROM session WHERE person_id = ? AND summary IS NOT NULL "
            "ORDER BY ended_at DESC, id DESC LIMIT 1",
            (person_id,),
        )
        return str(row["summary"]) if row else None

    def end(self, session_id: int, summary: str | None) -> None:
        self._db.execute(
            "UPDATE session SET ended_at = datetime('now'), summary = ? WHERE id = ?",
            (summary, session_id),
        )


class MessageRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, session_id: int, role: str, text: str, emotion: str | None = None) -> MessageRow:
        cur = self._db.execute(
            "INSERT INTO message(session_id, role, text, emotion) VALUES (?, ?, ?, ?)",
            (session_id, role, text, emotion),
        )
        assert cur.lastrowid is not None
        row = self._db.query_one("SELECT * FROM message WHERE id = ?", (cur.lastrowid,))
        assert row is not None
        return _to_message(row)

    def recent(self, session_id: int, limit: int) -> list[MessageRow]:
        rows = self._db.query_all(
            "SELECT * FROM (SELECT * FROM message WHERE session_id = ? "
            "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (session_id, limit),
        )
        return [_to_message(r) for r in rows]


def _to_person(r: sqlite3.Row) -> Person:
    return Person(
        id=r["id"],
        display_name=r["display_name"],
        role=r["role"],
        created_at=r["created_at"],
        last_seen_at=r["last_seen_at"],
    )


def _to_fact(r: sqlite3.Row) -> FactRow:
    return FactRow(
        id=r["id"],
        key=r["key"],
        value=r["value"],
        confidence=r["confidence"],
        updated_at=r["updated_at"],
    )


def _to_session(r: sqlite3.Row) -> SessionRow:
    return SessionRow(
        id=r["id"],
        person_id=r["person_id"],
        started_at=r["started_at"],
        ended_at=r["ended_at"],
        summary=r["summary"],
    )


def _to_message(r: sqlite3.Row) -> MessageRow:
    return MessageRow(
        id=r["id"],
        session_id=r["session_id"],
        role=r["role"],
        text=r["text"],
        emotion=r["emotion"],
        created_at=r["created_at"],
    )
