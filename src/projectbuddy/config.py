"""Typed application settings.

Settings choose which adapter (fake vs. real) backs each model seam. The defaults
run the fully-faked stack so CI and the cloud dev container work with no models
installed. Override via environment variables (prefix ``PB_``) or a ``.env`` file.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMBackend = Literal["fake", "ollama"]
STTBackend = Literal["fake", "faster_whisper"]
TTSBackend = Literal["fake", "piper", "kokoro"]
RecognitionBackend = Literal["fake", "insightface"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Model backends
    llm_backend: LLMBackend = "fake"
    stt_backend: STTBackend = "fake"
    tts_backend: TTSBackend = "fake"
    recognition_backend: RecognitionBackend = "fake"

    # Ollama (used only when llm_backend == "ollama")
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    llm_num_ctx: int = 4096

    # faster-whisper STT (used only when stt_backend == "faster_whisper")
    whisper_model: str = "base"  # tiny | base | small (latency/accuracy trade-off)
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str = "en"

    # Piper TTS (used only when tts_backend == "piper")
    piper_binary: str = "piper"
    piper_voice_path: str = ""  # path to a downloaded .onnx voice; see pull_models.sh

    # Kokoro TTS (used only when tts_backend == "kokoro")
    kokoro_voice: str = "af_heart"
    kokoro_lang: str = "a"  # 'a' = American English

    # Face recognition (used only when recognition_backend == "insightface")
    insightface_model: str = "buffalo_l"
    insightface_device: str = "cpu"  # or "cuda"
    # Cosine threshold for a confident match; conservative to avoid sibling mix-ups.
    recognition_match_threshold: float = 0.6

    # Data
    db_path: str = "buddy.db"

    # Memory tuning
    short_term_turns: int = 12  # recent turns kept verbatim in context


def get_settings() -> Settings:
    """Build settings from the environment. Override in tests via dependency injection."""
    return Settings()
