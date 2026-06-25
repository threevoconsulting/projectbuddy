# Protocol — the face ↔ brain contract

Source of truth: [`protocol/`](../src/projectbuddy/protocol/). All shapes are pydantic
models with contract tests under `tests/contract/`.

## LLM output envelope

The model must return **only** this JSON object ([`llm_envelope.py`](../src/projectbuddy/protocol/llm_envelope.py)):

```json
{
  "emotion": "excited",
  "say": "A stegosaurus? So cool! Want to hear a dino joke?",
  "remember": [{ "key": "favorite_dinosaur", "value": "stegosaurus" }]
}
```

- `emotion` ∈ `happy, curious, thinking, excited, confused, sleepy, sad, celebrating`
- `say` — the spoken line (1–3 short sentences), sent to TTS
- `remember` — optional durable facts (long-term memory)

The backend validates it; on failure it retries the model once with a stricter
instruction, then falls back to a safe default
(`{emotion: curious, say: "Hmm, can you say that again?"}`).

## REST (management)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness + version |
| `POST` | `/converse-text` | text-in → validated Buddy reply (the M3 demo path) |
| `POST` | `/session/start` | begin a session; returns the resume summary |
| `POST` | `/session/end` | end a session; writes the medium-term summary |
| `GET` | `/person` | list profiles |
| `POST` | `/person` | create a profile |
| `DELETE` | `/person/{id}` | **forget** — cascade-delete all of a person's data |
| `GET` | `/person/{id}/facts` | what Buddy remembers (parent transparency) |
| `POST` | `/enroll` · `/recognize` · `/consent` | Phase 2 |

## WebSocket `/ws/converse`

**Push-to-talk** (client → server): stream `audio` chunks while the mic is open, then
`end` to close the utterance and trigger a turn. An optional `start` selects/continues
a session; otherwise the connection lazily creates one and reuses it.

```
{"type":"start","session_id":7}          ← optional
{"type":"audio","chunk":"<base64 pcm>"}  ← 16 kHz mono 16-bit PCM
{"type":"end"}
```

Server → client during one turn, in order (**the face leads the voice**):

```
{"type":"state","value":"listening"}
{"type":"state","value":"thinking"}
{"type":"emotion","value":"excited"}     ← face animates now
{"type":"audio","chunk":"<base64 pcm>"}  ← TTS streams (22.05 kHz); mouth animates
{"type":"final","transcript":"...","say":"..."}
```

Empty/unintelligible input gets a gentle `emotion: confused` + a "say that again?" line,
with no LLM turn (TDD §NFR-3). Frame models live in
[`protocol/ws.py`](../src/projectbuddy/protocol/ws.py); the ordering (emotion before the
first audio chunk) is enforced in [`orchestrator/turn.py`](../src/projectbuddy/orchestrator/turn.py)
and asserted by [`tests/contract/test_ws_frames.py`](../tests/contract/test_ws_frames.py).
