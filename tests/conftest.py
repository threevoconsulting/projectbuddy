"""Shared fixtures. Everything is wired to the fakes + an in-memory DB, so the whole
suite runs with no models and leaves nothing on disk."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from projectbuddy.app import create_app
from projectbuddy.config import Settings
from projectbuddy.db.engine import Database
from projectbuddy.db.repositories import FactRepo, MessageRepo, PersonRepo, SessionRepo


@pytest.fixture
def settings() -> Settings:
    return Settings(
        db_path=":memory:",
        llm_backend="fake",
        stt_backend="fake",
        tts_backend="fake",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db() -> Iterator[Database]:
    database = Database(":memory:")
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def repos(db: Database) -> dict[str, object]:
    return {
        "persons": PersonRepo(db),
        "facts": FactRepo(db),
        "sessions": SessionRepo(db),
        "messages": MessageRepo(db),
    }
