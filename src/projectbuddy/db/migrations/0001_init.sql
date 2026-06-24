-- Phase 1 schema. Phase 2 (face_embedding, consent) arrives in a later migration.
-- ON DELETE CASCADE makes "forget this person" a single-row delete.

CREATE TABLE IF NOT EXISTS person (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL,
    role          TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at  TEXT
);

CREATE TABLE IF NOT EXISTS fact (
    id          INTEGER PRIMARY KEY,
    person_id   INTEGER REFERENCES person(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    confidence  REAL DEFAULT 1.0,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (person_id, key)
);

CREATE TABLE IF NOT EXISTS session (
    id           INTEGER PRIMARY KEY,
    person_id    INTEGER REFERENCES person(id) ON DELETE CASCADE,
    started_at   TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at     TEXT,
    summary      TEXT
);

CREATE TABLE IF NOT EXISTS message (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER REFERENCES session(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,          -- 'child' | 'buddy'
    text        TEXT NOT NULL,
    emotion     TEXT,                   -- emotion Buddy expressed, if role='buddy'
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fact_person ON fact(person_id);
CREATE INDEX IF NOT EXISTS idx_session_person ON session(person_id);
CREATE INDEX IF NOT EXISTS idx_message_session ON message(session_id);
