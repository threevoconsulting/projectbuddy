"""SQLite connection management + migrations.

A single :class:`Database` owns one connection (SQLite handles concurrency via WAL;
the app serializes writes through this connection). Foreign keys are enforced so the
``ON DELETE CASCADE`` rules actually fire. Pass ``":memory:"`` in tests.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        # check_same_thread=False because FastAPI may touch the connection from a
        # threadpool; _lock serializes access to keep that safe.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._configure()
        self._migrate()

    def _configure(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            # WAL is unavailable for in-memory DBs; ignore failures there.
            try:
                self._conn.execute("PRAGMA journal_mode = WAL")
            except sqlite3.OperationalError:
                pass

    def _migrate(self) -> None:
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
            )
            applied = {
                row["name"] for row in self._conn.execute("SELECT name FROM schema_migrations")
            }
            for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
                if sql_file.name in applied:
                    continue
                self._conn.executescript(sql_file.read_text(encoding="utf-8"))
                self._conn.execute(
                    "INSERT INTO schema_migrations(name) VALUES (?)", (sql_file.name,)
                )
            self._conn.commit()

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query_one(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Row | None:
        with self._lock:
            row: sqlite3.Row | None = self._conn.execute(sql, params).fetchone()
            return row

    def query_all(self, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
