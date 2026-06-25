# Phase 2 — Perception & Continuity (planned)

Phase 2 is additive: it builds on the same brain, face, and data model. Milestones
M7–M9 in the build plan.

## Recognition (M7) — implemented

The seam, consent gate, persistence, and REST endpoints are built; only the in-browser
capture UI is deferred to the M9 parent app (a `?camtest=1` dev affordance exercises the
endpoints in the meantime).

- **Embed → Match.** The seam is deliberately thin: the recognizer's only job is
  `embed(image) -> 512-d vector | None`. Averaging enrollment frames and matching a probe
  by cosine similarity are pure-Python helpers in
  [`core/recognition.py`](../src/projectbuddy/core/recognition.py) — no numpy on the CI
  path. Embeddings are stored as JSON in SQLite.
- **Embedding model.** This is a **home-use** project, so the original commercial-license
  constraint no longer applies — **InsightFace** with its standard pretrained packs
  (`buffalo_l`) is the path. The seam keeps any alternative a drop-in if ever wanted.
- **Seam:** `FaceRecognizer` Protocol with a `fake` adapter (CI, deterministic from the
  image bytes so enroll→recognize round-trips) and an InsightFace adapter (Mac, lazy
  imports), mirroring the LLM/STT/TTS pattern. Select with `PB_RECOGNITION_BACKEND`.
- **Enrollment is parent-gated** — `POST /person/{id}/enroll` returns **403** unless a
  granted `consent` row for scope `face` exists. It averages one or more capture frames
  into one vector per person. Consent is managed via `POST`/`GET /person/{id}/consent`.
- **Recognition** — `POST /recognize` matches against enrolled vectors using
  `PB_RECOGNITION_MATCH_THRESHOLD` (default 0.45 — ArcFace same-person cosine is ~0.5–0.7,
  different-person ~0.0–0.3). Re-enrollment is just another enroll (kids' faces change
  fast). The frontend recognizes before enrolling, so a known face is greeted rather
  than duplicated.
- **Templates, not media** — images arrive base64 in JSON, are embedded in memory, and are
  **never written to disk**; only the vector is persisted.
- **Camera-active indicator** in the face UI shows whenever a camera stream is live.

## Continuity & privacy (M8) — implemented

The camera and chat are one experience: on the main `/app/` screen Buddy sees who's
there, binds the conversation to their profile, and greets them out loud.

- **Recognize → resume.** The frontend polls `/recognize`; when the person changes it
  calls `POST /session/start` for them, so voice and text turns use *their* memory
  (facts + last-session summary). The WS sends a `start` frame so spoken turns bind too.
- **Spoken greeting.** A WS `hello` frame runs `run_greeting`: Buddy welcomes the person
  by name in its real voice, drawing on what it remembers (no synthetic child turn is
  stored). Face leads the voice, same as a normal turn.
- **Retention job.** `core/retention.sweep_face_retention` deletes face embeddings past
  `consent.retention_until` and revokes them. It runs at startup, on a timer
  (`PB_RETENTION_SWEEP_SECONDS`, default 6 h), and on demand via `POST /retention/run`.
- **Revoke = delete.** Revoking face consent (`POST /person/{id}/consent` with
  `granted:false`) removes the stored template immediately. `DELETE /person/{id}` still
  cascades to everything (verified by tests).
- **Deferred:** optional **liveness** (Silent-Face MiniFASNet) to reject photo spoofs,
  and a hardware **camera LED** to complement the on-screen indicator.

## Parent companion app (M9)

The six mockup screens — Welcome, Conversation, Sessions, Dashboard, Profile, Memory —
built with the same vanilla front-end against the existing REST endpoints (the Memory
screen is the `GET /person/{id}/facts` + per-fact delete surface).

## Path to the robot

The web face runs unchanged in Chromium kiosk on the robot's Pi screen; the brain stays
on the Mac. Servo head-motion subscribes to the same `emotion`/`state` events that drive
on-screen head tilt — the expression engine's `(state, amplitude)` interface is the
integration seam.
