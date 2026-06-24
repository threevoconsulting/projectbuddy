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
- **Phase 2** — biometric capture is gated behind verifiable parental **consent**; only
  face **templates** are stored (never images); a **retention** job enforces deletion
  windows; a camera-active indicator satisfies notice. See
  [`phase2-perception.md`](phase2-perception.md).

These controls map to COPPA (consent-before-capture, retention, deletion, access), US
state biometric law (notice + consent), and Canadian PIPEDA / Quebec Law 25.
