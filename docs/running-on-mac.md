# Running the real stack on a Mac

The cloud dev container and CI run the **faked** stack (no models). The real voice loop
runs on a household Apple-Silicon Mac (≥16 GB unified memory recommended).

## 1. Install

```bash
uv sync --extra mac        # faster-whisper, piper-tts, webrtcvad (M4)
```

Install [Ollama](https://ollama.com) and start it (`ollama serve` / the menubar app).

## 2. Pull models

```bash
./scripts/pull_models.sh
```

LLM choice by RAM (verify exact tags before pulling; all must be commercially usable):

| Mac RAM | Model | Notes |
|---|---|---|
| 8 GB | `gemma3:4b` / `llama3.2:3b` | "small brain"; fastest |
| 16 GB | `qwen3:8b` (default) | best warmth/latency balance |
| 32 GB+ | `gemma3:27b` | higher quality |

Use Q4_K_M quantization; keep `OLLAMA_MAX_LOADED_MODELS=1` and a 4–8k context to protect
latency and memory.

## 3. Run

```bash
export PB_PIPER_VOICE_PATH=./models/piper/en_US-lessac-high.onnx   # from pull_models.sh
./scripts/run_mac.sh       # PB_LLM_BACKEND=ollama, STT=faster_whisper, TTS=piper
```

**Buddy's voice** is `en_US-lessac-high` by default (clear and friendly); `en_US-amy-medium`
is a warmer alternative. For a more lifelike voice, set `PB_TTS_BACKEND=kokoro`. Compare
candidates side by side with `uv run python scripts/compare_voices.py` — it writes a WAV
per voice to `./voice-samples/` so you can listen and pick.

Open the face full-screen at <http://localhost:8000/app/> and **hold the 🎤 button to
talk** (push-to-talk); release and Buddy replies, expression first, then voice.

> **Microphone access** needs a secure context: `localhost` works directly, but an iPad
> pointed at the Mac over Wi-Fi (`http://<mac-ip>:8000/app/`) will not get mic permission
> over plain HTTP — front it with HTTPS (e.g. a local reverse proxy) for the tablet
> "device on the desk" demo. The text box works everywhere as a fallback.

## 4. Smoke-test (M4+)

```bash
uv run pytest -m smoke_mac
```

These tests (deselected in CI) assert the real model emits a valid envelope, end-to-end
latency ≤ 2.0 s, and TTS streams. Configure via env vars (`PB_OLLAMA_MODEL`, etc.); see
[`.env.example`](../.env.example).
