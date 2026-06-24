# Data model & memory

A single local SQLite file (`buddy.db`, configurable via `PB_DB_PATH`). Schema lives in
[`db/migrations/`](../src/projectbuddy/db/migrations/) and is applied at startup; all
access goes through [`repositories.py`](../src/projectbuddy/db/repositories.py).

## Phase 1 tables

| table | purpose |
|---|---|
| `person` | people Buddy knows (Phase 1: a single default profile suffices) |
| `fact` | durable preferences/facts — **long-term memory** (`UNIQUE(person_id, key)`) |
| `session` | a conversation; `summary` is the **medium-term** resume seed |
| `message` | individual turns (`child` / `buddy`), with Buddy's expressed emotion |

`PRAGMA foreign_keys = ON` and `ON DELETE CASCADE` throughout mean **"forget this
person" is a single-row delete** that removes their facts, sessions, and messages. WAL
mode is enabled for on-disk databases.

Phase 2 adds `face_embedding` (templates, never images) and `consent` (consent +
retention audit). See [`phase2-perception.md`](phase2-perception.md).

## The three memory tiers

Implemented in [`core/memory.py`](../src/projectbuddy/core/memory.py):

- **Short-term** — the last `PB_SHORT_TERM_TURNS` turns, kept verbatim in the prompt.
- **Medium-term** — a per-session `summary` written at `/session/end`, returned by the
  next `/session/start` so Buddy can "pick up where we left off."
- **Long-term** — `fact` rows persisted from the model's `remember[]`, injected into the
  system prompt.

`build_context()` assembles the LLM message list; `commit_turn()` persists an exchange +
facts; `summarize_session()` writes the medium-term summary.
