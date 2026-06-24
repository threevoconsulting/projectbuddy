#!/usr/bin/env bash
# Mac-only: fetch the local models Buddy's real stack needs. Safe to re-run.
# Nothing here is required for CI or the faked dev stack.
set -euo pipefail

MODEL="${PB_OLLAMA_MODEL:-qwen3:8b}"

echo "==> Pulling Ollama model: $MODEL"
if command -v ollama >/dev/null 2>&1; then
  ollama pull "$MODEL"
else
  echo "   ollama not found — install from https://ollama.com and re-run." >&2
fi

cat <<'NOTE'

==> Piper (TTS) and Whisper (STT) assets are downloaded by their Python packages
    on first use, or place voice files under ./models/. See docs/running-on-mac.md
    for the recommended Piper voice and faster-whisper model size.
NOTE
