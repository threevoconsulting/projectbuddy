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
from projectbuddy.db.repositories import (
    ConsentRepo,
    FaceEmbeddingRepo,
    FactRepo,
    MessageRepo,
    PersonRepo,
    SessionRepo,
)
from projectbuddy.models.liveness.base import LivenessDetector
from projectbuddy.models.llm.base import LLMClient
from projectbuddy.models.recognition.base import FaceRecognizer
from projectbuddy.models.stt.base import STTEngine
from projectbuddy.models.tts.base import TTSEngine


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


def _build_stt(settings: Settings) -> STTEngine:
    if settings.stt_backend == "faster_whisper":
        from projectbuddy.models.stt.faster_whisper import FasterWhisperSTTEngine

        return FasterWhisperSTTEngine(
            model=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            language=settings.whisper_language,
        )
    from projectbuddy.models.stt.fake import FakeSTTEngine

    return FakeSTTEngine()


def _build_tts(settings: Settings) -> TTSEngine:
    if settings.tts_backend == "piper":
        from projectbuddy.models.tts.piper import PiperTTSEngine

        return PiperTTSEngine(
            voice_path=settings.piper_voice_path,
            binary=settings.piper_binary,
        )
    if settings.tts_backend == "kokoro":
        from projectbuddy.models.tts.kokoro import KokoroTTSEngine

        return KokoroTTSEngine(
            voice=settings.kokoro_voice,
            lang_code=settings.kokoro_lang,
        )
    from projectbuddy.models.tts.fake import FakeTTSEngine

    return FakeTTSEngine()


def _build_recognition(settings: Settings) -> FaceRecognizer:
    if settings.recognition_backend == "insightface":
        from projectbuddy.models.recognition.insightface import InsightFaceRecognizer

        return InsightFaceRecognizer(
            model=settings.insightface_model,
            device=settings.insightface_device,
        )
    from projectbuddy.models.recognition.fake import FakeRecognizer

    return FakeRecognizer()


def _build_liveness(settings: Settings) -> LivenessDetector:
    if settings.liveness_backend == "minifasnet":
        from projectbuddy.models.liveness.minifasnet import MiniFasnetLivenessDetector

        return MiniFasnetLivenessDetector(
            model=settings.liveness_model,
            device=settings.liveness_device,
            threshold=settings.liveness_threshold,
        )
    from projectbuddy.models.liveness.fake import FakeLivenessDetector

    return FakeLivenessDetector()


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
    stt: STTEngine
    tts: TTSEngine
    recognition: FaceRecognizer
    liveness: LivenessDetector
    face_embeddings: FaceEmbeddingRepo
    consents: ConsentRepo

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
            stt=_build_stt(settings),
            tts=_build_tts(settings),
            recognition=_build_recognition(settings),
            liveness=_build_liveness(settings),
            face_embeddings=FaceEmbeddingRepo(db),
            consents=ConsentRepo(db),
        )


def get_container(request: Request) -> Container:
    container = request.app.state.container
    assert isinstance(container, Container)
    return container
