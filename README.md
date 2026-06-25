# Project Buddy

A **local-first AI companion for children** (Threevo). A child talks to Buddy out loud;
Buddy listens, thinks (a local LLM via Ollama), speaks back, and an expressive animated
face reacts in real time. Everything runs on household hardware — **no cloud, no child
data leaves the home.**

Built **brain-first** in two phases:

- **Phase 1 — Interactive Brain:** voice conversation + the animated face. *(in progress)*
- **Phase 2 — Perception & Continuity:** family face recognition, per-person memory,
  consent/retention, and a parent companion app. *(planned)*

See [`docs/architecture.md`](docs/architecture.md) for the full design, and the build
plan for milestones.

## How it's structured

The **brain** (Python/FastAPI backend) orchestrates STT → LLM → TTS and owns memory
(SQLite). The **face** (vanilla HTML/CSS/SVG/JS, no build step) renders Buddy and talks
to the brain over HTTP/WebSocket. The same face artifact runs in a browser today and in
a Raspberry Pi Chromium kiosk later.

Every external model (LLM, STT, TTS) sits behind a small interface with a **fake**
adapter. The default stack is fully faked, so **CI and this repo run with no models
installed**; the real models run on a Mac (see below).

```
src/projectbuddy/
  app.py            FastAPI factory (+ /health, mounts the face at /app/)
  config.py deps.py settings + adapter wiring (fake ↔ real by env var)
  protocol/         the contracts: llm_envelope (emotion/say/remember), ws, rest
  api/              converse-text, person, session, ws_converse  (perception → later)
  orchestrator/     turn.py — one turn as a stream of frames (text + voice share it)
  core/             output_parser, safety, memory
  db/               schema migrations, engine, repositories
  models/llm/       LLMClient Protocol + fake + ollama
  models/stt/       STTEngine Protocol + fake + faster_whisper
  models/tts/       TTSEngine Protocol + fake + piper
  web/              the face (index.html, css, js/face.js, audio, ws-client, PWA)
tests/              unit · contract · integration  (all on fakes)
```

## Quickstart (no models needed)

Requires [uv](https://docs.astral.sh/uv/).

```bash
make setup           # uv sync (fakes only)
make lint && make types && make test
make run             # http://127.0.0.1:8765  → face at /app/
```

- **Talk to Buddy (voice):** open <http://127.0.0.1:8765/app/> and **hold 🎤 to talk**
  (push-to-talk over `WS /ws/converse`). On the faked stack STT/TTS are stand-ins — the
  loop, frame ordering, and face animation are real; a real voice needs the Mac stack.
- **Talk to Buddy (text):** type in the same screen — the faked brain replies with an
  emotion + line and the face reacts.
- **Face QA, no backend:** open <http://127.0.0.1:8765/app/?mock=1> to cycle all eight
  expressions with a simulated speaking mouth.
- **Kiosk layout:** add `?kiosk=1` to hide the text controls.

## Running the real stack (on a Mac)

```bash
uv sync --extra mac
./scripts/pull_models.sh      # ollama pull + Piper voices (lessac-high, amy-medium)
export PB_PIPER_VOICE_PATH=./models/piper/en_US-lessac-high.onnx
./scripts/run_mac.sh          # LLM=ollama, STT=faster-whisper, TTS=piper
```

See [`docs/running-on-mac.md`](docs/running-on-mac.md). The Mac runs the real **LLM**
(Ollama) plus **voice** — Whisper STT + Piper TTS over `WS /ws/converse`. Buddy's default
voice is `en_US-lessac-high`; for a more lifelike one set `PB_TTS_BACKEND=kokoro`. Compare
voices with `uv run python scripts/compare_voices.py` (writes a WAV per voice to
`./voice-samples/`). Latency + streaming are checked on the real stack with
`uv run pytest -m smoke_mac` (deselected in CI).

## Make targets

| target | what |
|---|---|
| `make setup` | install deps (fakes only) |
| `make lint` / `make types` / `make test` | ruff · mypy · pytest |
| `make redteam` | safety gate over the red-team corpus |
| `make run` | backend with the faked stack |
| `make run-mac` | backend with the real models |

## Privacy

Buddy is local-first by construction: inference and data stay on household hardware.
Children's data is never sent to a third party. Deletion ("forget this person") and
memory transparency are first-class. See [`docs/safety.md`](docs/safety.md).
