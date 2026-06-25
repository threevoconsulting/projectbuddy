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
LivenessBackend = Literal["fake", "minifasnet"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8765

    # Model backends
    llm_backend: LLMBackend = "fake"
    stt_backend: STTBackend = "fake"
    tts_backend: TTSBackend = "fake"
    recognition_backend: RecognitionBackend = "fake"
    liveness_backend: LivenessBackend = "fake"

    # Ollama (used only when llm_backend == "ollama")
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"  # small & fast; bump to qwen3:8b / gemma3 for quality
    llm_num_ctx: int = 2048  # smaller window = faster prompt processing; replies are tiny
    llm_num_predict: int = 128  # cap generation — Buddy says 1-3 short sentences
    llm_keep_alive: str = "30m"  # keep the model resident between turns (no reload latency)

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
    # Cosine threshold for a confident match. ArcFace/buffalo_l same-person cosine is
    # typically 0.5-0.7 and different-person 0.0-0.3, so 0.45 separates them well;
    # raise it if siblings get confused, lower it if a known face isn't recognized.
    recognition_match_threshold: float = 0.45

    # Liveness / anti-spoof (used only when liveness_backend == "minifasnet"). The fake
    # backend is permissive (any real frame passes); the real adapter loads a MiniFASNet
    # ONNX model from liveness_model and rejects spoofs below liveness_threshold.
    liveness_model: str = ""  # path to a MiniFASNet .onnx; required for the real backend
    liveness_device: str = "cpu"
    liveness_threshold: float = 0.5

    # Data
    db_path: str = "buddy.db"

    # Memory tuning
    short_term_turns: int = 8  # recent turns kept verbatim in context (smaller = faster)

    # Retention sweep cadence (M8): how often to delete face data past its
    # consent.retention_until. Default 6 hours; also runs at startup and on demand.
    retention_sweep_seconds: int = 21_600


def get_settings() -> Settings:
    """Build settings from the environment. Override in tests via dependency injection."""
    return Settings()
