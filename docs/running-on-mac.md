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
./scripts/run_mac.sh       # PB_LLM_BACKEND=ollama (+ STT/TTS in M4)
```

Open the face full-screen at <http://localhost:8000/app/>, or point an iPad at the Mac
over Wi-Fi as a PWA (`http://<mac-ip>:8000/app/`) for the "device on the desk" feel.

## 4. Smoke-test (M4+)

```bash
uv run pytest -m smoke_mac
```

These tests (deselected in CI) assert the real model emits a valid envelope, end-to-end
latency ≤ 2.0 s, and TTS streams. Configure via env vars (`PB_OLLAMA_MODEL`, etc.); see
[`.env.example`](../.env.example).
