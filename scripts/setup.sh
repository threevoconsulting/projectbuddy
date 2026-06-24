#!/usr/bin/env bash
# Idempotent dev setup for CI and the cloud dev container.
# Installs ONLY the faked stack — no Ollama/Whisper/Piper model runtimes.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — install from https://docs.astral.sh/uv/ and re-run." >&2
  exit 1
fi

echo "==> Syncing dependencies (dev + default, no model extras)…"
uv sync

echo "==> Done. Try: make lint && make types && make test"
