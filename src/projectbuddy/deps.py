"""Adapter wiring.

Builds one container of concrete adapters (chosen by :class:`Settings`) and exposes
FastAPI dependencies that read it off ``app.state``. Swapping fake ↔ real is an env
change only; nothing downstream imports a concrete backend.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from projectbuddy.config import Settings
from projectbuddy.core.memory import MemoryManager
from projectbuddy.db.engine import Database
from projectbuddy.db.repositories import FactRepo, MessageRepo, PersonRepo, SessionRepo
from projectbuddy.models.llm.base import LLMClient


def _build_llm(settings: Settings) -> LLMClient:
    if settings.llm_backend == "ollama":
        from projectbuddy.models.llm.ollama import OllamaLLMClient

        return OllamaLLMClient(
            url=settings.ollama_url,
            model=settings.ollama_model,
            num_ctx=settings.llm_num_ctx,
        )
    from projectbuddy.models.llm.fake import FakeLLMClient

    return FakeLLMClient()


@dataclass
class Container:
    settings: Settings
    db: Database
    persons: PersonRepo
    facts: FactRepo
    sessions: SessionRepo
    messages: MessageRepo
    memory: MemoryManager
    llm: LLMClient

    @classmethod
    def build(cls, settings: Settings) -> Container:
        db = Database(settings.db_path)
        facts = FactRepo(db)
        sessions = SessionRepo(db)
        messages = MessageRepo(db)
        return cls(
            settings=settings,
            db=db,
            persons=PersonRepo(db),
            facts=facts,
            sessions=sessions,
            messages=messages,
            memory=MemoryManager(
                facts=facts,
                sessions=sessions,
                messages=messages,
                short_term_turns=settings.short_term_turns,
            ),
            llm=_build_llm(settings),
        )


def get_container(request: Request) -> Container:
    container = request.app.state.container
    assert isinstance(container, Container)
    return container
