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

## WebSocket `/ws/converse` (wired in M4)

Server → client during one turn, in order (**the face leads the voice**):

```
{"type":"state","value":"listening"}
{"type":"state","value":"thinking"}
{"type":"emotion","value":"excited"}     ← face animates now
{"type":"audio","chunk":"<base64 pcm>"}  ← TTS streams; mouth animates
{"type":"final","transcript":"...","say":"..."}
```

Frame models live in [`protocol/ws.py`](../src/projectbuddy/protocol/ws.py); the ordering
(emotion before the first audio chunk) is enforced in the orchestrator and asserted by a
contract test.
