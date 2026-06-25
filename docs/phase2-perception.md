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
  `PB_RECOGNITION_MATCH_THRESHOLD` (default 0.6 — conservative, to avoid sibling
  confusion). Re-enrollment is just another enroll (kids' faces change fast).
- **Templates, not media** — images arrive base64 in JSON, are embedded in memory, and are
  **never written to disk**; only the vector is persisted.
- **Camera-active indicator** in the face UI shows whenever a camera stream is live.

## Continuity & privacy (M8)

- Per-person profiles, facts, and sessions; on recognizing a returning person, load the
  latest summary + facts and resume.
- **Retention job** enforces `retention_until`; `DELETE /person/{id}` cascades (verified by
  compliance tests).
- Optional **liveness** (Silent-Face MiniFASNet, Apache-2.0) to reject photo spoofs.
- Hardware **camera LED** to complement the on-screen camera-active indicator (added in M7).

## Parent companion app (M9)

The six mockup screens — Welcome, Conversation, Sessions, Dashboard, Profile, Memory —
built with the same vanilla front-end against the existing REST endpoints (the Memory
screen is the `GET /person/{id}/facts` + per-fact delete surface).

## Path to the robot

The web face runs unchanged in Chromium kiosk on the robot's Pi screen; the brain stays
on the Mac. Servo head-motion subscribes to the same `emotion`/`state` events that drive
on-screen head tilt — the expression engine's `(state, amplitude)` interface is the
integration seam.
