# Safety & privacy

Buddy is for young children, so safety and privacy are product requirements, not
add-ons.

## Layered safety

1. **Constrained system prompt** ([`config/system_prompt.md`](../config/system_prompt.md))
   — Buddy stays in character, keeps language age-appropriate, and gently redirects
   unsafe topics.
2. **Structured output** — the model must return the JSON envelope; the parser validates,
   retries once, then falls back to a safe default. Malformed output can never reach the
   child as-is.
3. **Post-generation filter** ([`core/safety.py`](../src/projectbuddy/core/safety.py)) —
   every line Buddy is about to speak is checked; blocked lines are replaced with a safe
   substitute. Baseline today is a deny-list; **M5 expands it with the red-team corpus
   and (optionally) a local classifier.**

### The red-team gate

`make redteam` runs [`tests/fixtures/redteam.txt`](../tests/fixtures/redteam.txt) through
the filter; every sample must be blocked. The bar before any child testing is **100%
safe, zero unsafe outputs** (BRD KPI). Expand the corpus as new risks are found.

## Privacy by construction

- **Local-only data plane** — services bind to the LAN; no telemetry of content.
- **Deletion is first-class** — `DELETE /person/{id}` cascades to all of a person's data.
- **Transparency** — `GET /person/{id}/facts` shows exactly what Buddy remembers (COPPA
  access).
- **Phase 2** — biometric enrollment is gated behind a parental **consent** row (M7:
  `POST /person/{id}/enroll` returns 403 without it); only face **templates** are stored —
  images are embedded in memory and never written to disk; a camera-active indicator
  satisfies notice (M7). **Retention** is enforced (M8): a sweep deletes face templates
  past `consent.retention_until` (startup, timer, and `POST /retention/run`), and revoking
  face consent deletes the template immediately. See
  [`phase2-perception.md`](phase2-perception.md).

This is a **home-use** project, so the children's-privacy legal regime (COPPA, US state
biometric law, PIPEDA / Quebec Law 25) is not a compliance obligation here. The controls
above are kept anyway because they're simply good practice for a device a child talks to —
local-only data, easy deletion, and full transparency for the parent who runs it.
