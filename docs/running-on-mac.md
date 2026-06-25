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
| 8 GB | `llama3.2:3b` (default) / `gemma3:4b` | "small brain"; fastest responses |
| 16 GB | `qwen3:8b` | warmer/smarter, a bit slower |
| 32 GB+ | `gemma3:27b` | highest quality |

Use Q4_K_M quantization; keep `OLLAMA_MAX_LOADED_MODELS=1` and a 4–8k context to protect
latency and memory.

## 3. Run

```bash
./scripts/run_mac.sh       # LLM=ollama, STT=faster_whisper, TTS=kokoro, recognition=insightface
```

**Buddy's voice** defaults to **Kokoro** (`af_heart`) — a warm, natural neural voice that's
kinder for young children than Piper's more synthetic tone. For a faster, lighter voice set
`PB_TTS_BACKEND=piper` (defaults to the warmer `en_US-amy-medium`; `en_US-lessac-high` is the
crisper alternative). Compare them with `uv run python scripts/compare_voices.py` — it writes a
WAV per voice to `./voice-samples/` so you can listen and pick. Pick a different Kokoro voice
with `PB_KOKORO_VOICE` (see the Kokoro voice list).

### Tuning response speed
Latency is dominated by the LLM. Levers (all env vars):
- `PB_OLLAMA_MODEL` — a smaller model replies faster: `llama3.2:3b` / `gemma3:4b` (8 GB),
  `qwen3:8b` (default, 16 GB).
- `PB_LLM_NUM_PREDICT=128` caps reply length, `PB_LLM_NUM_CTX=2048` shrinks the context, and
  `PB_LLM_KEEP_ALIVE=30m` keeps the model resident between turns — all on by default now.
- `PB_WHISPER_MODEL=tiny` speeds up speech-to-text (vs `base`). `make run-mac` pre-warms the
  LLM at startup so the first turn isn't cold.

Open the face full-screen at <http://localhost:8765/app/> and **hold the 🎤 button to
talk** (push-to-talk); release and Buddy replies, expression first, then voice. The
**parent app** is at <http://localhost:8765/parent/> (sessions, transcripts, memory,
consent, delete).

**Anti-spoof (optional):** set `PB_LIVENESS_BACKEND=minifasnet` and
`PB_LIVENESS_MODEL=<path-to-minifasnet.onnx>` to reject printed-photo spoofs at enroll/
recognize. Without it (default `fake`), liveness is permissive.

> **Microphone access** needs a secure context: `localhost` works directly, but an iPad
> pointed at the Mac over Wi-Fi (`http://<mac-ip>:8765/app/`) will not get mic permission
> over plain HTTP — front it with HTTPS (e.g. a local reverse proxy) for the tablet
> "device on the desk" demo. The text box works everywhere as a fallback.

## 4. Smoke-test (M4+)

```bash
uv run pytest -m smoke_mac
```

These tests (deselected in CI) assert the real model emits a valid envelope, end-to-end
latency ≤ 2.0 s, and TTS streams. Configure via env vars (`PB_OLLAMA_MODEL`, etc.); see
[`.env.example`](../.env.example).
