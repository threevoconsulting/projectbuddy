# Architecture

Buddy is a **decoupled brain + face**, both running on the household LAN.

```
 FACE (front-end, web/PWA)                 BRAIN (backend, Python on the Mac)
 ┌──────────────────────────┐             ┌──────────────────────────────────┐
 │ Animated SVG face         │  HTTP / WS  │ FastAPI gateway                   │
 │ + expression state machine│ ◀─────────▶ │  ├─ Voice: STT (Whisper)  [M4]    │
 │ Mic capture / audio out   │             │  ├─ Brain: Ollama client          │
 │ [P2] Camera capture       │             │  ├─ Voice: TTS (Piper)    [M4]    │
 └──────────────────────────┘             │  ├─ Output parser + safety        │
                                           │  ├─ Memory manager                │
                                           │  └─ [P2] Recognition service      │
                                           └──────────┬───────────────────────┘
                                          Ollama (localhost) + SQLite (buddy.db)
```

## Principles

1. **Local-first.** All inference and data stay on household hardware.
2. **Seams over backends.** Each model (LLM/STT/TTS/recognition) is reached through a
   Python `Protocol` with a `fake` adapter (CI/dev) and a `real` adapter (Mac). Backend
   choice is an env var — see [`config.py`](../src/projectbuddy/config.py).
3. **The protocol is the contract.** The LLM envelope and the WS/REST frames are pydantic
   models with contract tests (see [`protocol.md`](protocol.md)).
4. **Portable face.** Vanilla web UI, no build step → runs unchanged in a Pi Chromium kiosk.

## The conversation loop

```
Child speaks
  → Face streams audio to the backend (WS)                         [M4]
  → STT transcribes (VAD finds end-of-utterance)                   [M4]
  → MemoryManager builds context (system prompt + facts + summary + recent turns)
  → LLM returns {emotion, say, remember[]}
  → output_parser validates (retry once, else safe fallback)
  → safety filter checks `say`
  → emotion → Face (animate FIRST); say → TTS → audio → Face; remember[] → memory
Loop.
```

In Phase 1 the text path (`POST /converse-text`) exercises everything except audio; M4
adds the streaming WebSocket loop that reuses the same orchestration.

## Why a local web app

One face codebase renders on a Mac, an iPad PWA, and the eventual Pi screen; the browser
provides mic/speaker/camera; the brain stays on the Mac with Ollama. See the TDD for the
full rationale and the path to embodiment (`docs/phase2-perception.md`).
