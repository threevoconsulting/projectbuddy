-- Phase 2a (M7): face recognition + parental consent.
-- Both tables hang off person with ON DELETE CASCADE, so "forget this person"
-- (DELETE /person/{id}) still removes every trace, including the face embedding.

-- One averaged face embedding per person, stored as a JSON array of floats (no
-- numpy/binary dependency leaks into persistence). `frames` records how many capture
-- frames were averaged into the vector.
CREATE TABLE IF NOT EXISTS face_embedding (
    id          INTEGER PRIMARY KEY,
    person_id   INTEGER REFERENCES person(id) ON DELETE CASCADE,
    vector      TEXT NOT NULL,          -- JSON list[float], length 512
    frames      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (person_id)
);

-- Parental consent, scoped (currently only 'face'). granted=0 keeps an auditable
-- "revoked" row rather than deleting history. retention_until is unused in M7 and
-- reserved for the M8 retention job.
CREATE TABLE IF NOT EXISTS consent (
    id               INTEGER PRIMARY KEY,
    person_id        INTEGER REFERENCES person(id) ON DELETE CASCADE,
    scope            TEXT NOT NULL,     -- 'face' (future: 'voice', ...)
    granted          INTEGER NOT NULL DEFAULT 0,
    granted_at       TEXT,
    granted_by       TEXT,              -- parent identifier / email, for the audit trail
    retention_until  TEXT,             -- reserved for M8 retention
    notes            TEXT,
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (person_id, scope)
);

CREATE INDEX IF NOT EXISTS idx_face_embedding_person ON face_embedding(person_id);
CREATE INDEX IF NOT EXISTS idx_consent_person ON consent(person_id);
