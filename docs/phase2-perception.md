# Phase 2 — Perception & Continuity (planned)

Phase 2 is additive: it builds on the same brain, face, and data model. Milestones
M7–M9 in the build plan.

## Recognition (M7)

- **Capture → Detect → Embed → Match.** The face sends a crop; the backend detects/aligns
  (SCRFD/RetinaFace-class), embeds (ArcFace-style 512-d), and matches by cosine similarity
  against enrolled vectors in SQLite.
- **Embedding model.** This is a **home-use** project, so the original commercial-license
  constraint no longer applies — **InsightFace** with its standard pretrained packs (e.g.
  `buffalo_l`) is the simplest path. (InspireFace remains a drop-in alternative behind the
  same seam if a commercial posture is ever wanted again.)
- **Enrollment is parent-gated** — blocked unless a valid `consent` row for scope `face`
  exists. Capture several frames, average the embedding, store one vector per person.
- **Children-specific** — conservative match threshold (avoid sibling confusion) and
  supported re-enrollment (kids' faces change fast).
- **Templates, not media** — discard frames immediately after embedding; never write child
  images to disk. (Still good practice at home: it keeps the data footprint tiny.)
- Seam: `FaceRecognizer` Protocol with a `fake` adapter (CI) and an InsightFace adapter
  (Mac), mirroring the LLM/STT/TTS pattern.

## Continuity & privacy (M8)

- Per-person profiles, facts, and sessions; on recognizing a returning person, load the
  latest summary + facts and resume.
- **Retention job** enforces `retention_until`; `DELETE /person/{id}` cascades (verified by
  compliance tests).
- Optional **liveness** (Silent-Face MiniFASNet, Apache-2.0) to reject photo spoofs.
- **Camera-active indicator** in the face UI (and later a hardware LED).

## Parent companion app (M9)

The six mockup screens — Welcome, Conversation, Sessions, Dashboard, Profile, Memory —
built with the same vanilla front-end against the existing REST endpoints (the Memory
screen is the `GET /person/{id}/facts` + per-fact delete surface).

## Path to the robot

The web face runs unchanged in Chromium kiosk on the robot's Pi screen; the brain stays
on the Mac. Servo head-motion subscribes to the same `emotion`/`state` events that drive
on-screen head tilt — the expression engine's `(state, amplitude)` interface is the
integration seam.
