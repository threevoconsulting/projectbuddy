#!/usr/bin/env bash
# Mac-only: fetch the local models Buddy's real stack needs. Safe to re-run.
# Nothing here is required for CI or the faked dev stack.
set -euo pipefail

MODEL="${PB_OLLAMA_MODEL:-llama3.2:3b}"

echo "==> Pulling Ollama model: $MODEL"
if command -v ollama >/dev/null 2>&1; then
  ollama pull "$MODEL"
else
  echo "   ollama not found — install from https://ollama.com and re-run." >&2
fi

echo "==> Piper voices (TTS)"
VOICE_DIR="${PB_VOICE_DIR:-./models/piper}"
mkdir -p "$VOICE_DIR"
ROOT="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"

# Buddy's default voice is en_US-lessac-high (clear, friendly). amy-medium is a warmer
# alternative — both are fetched so you can A/B with scripts/compare_voices.py.
fetch_voice() {
  local rel="$1" name="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fL -o "$VOICE_DIR/$name.onnx"      "$ROOT/$rel/$name.onnx"      || true
    curl -fL -o "$VOICE_DIR/$name.onnx.json" "$ROOT/$rel/$name.onnx.json" || true
  else
    echo "   curl not found — download $name manually from $ROOT/$rel/" >&2
  fi
}

fetch_voice "lessac/high"  "en_US-lessac-high"
fetch_voice "amy/medium"   "en_US-amy-medium"

echo "   Default voice: $VOICE_DIR/en_US-lessac-high.onnx"
echo "   Set: export PB_PIPER_VOICE_PATH=$VOICE_DIR/en_US-lessac-high.onnx"

cat <<'NOTE'

==> faster-whisper (STT) model weights download automatically on first use
    (cached under ~/.cache/huggingface). Pick the size with PB_WHISPER_MODEL
    (tiny|base|small). See docs/running-on-mac.md.

==> (optional) Kokoro TTS — a more lifelike voice — installs via `uv sync --extra mac`;
    its weights download on first use. Try it with PB_TTS_BACKEND=kokoro.
NOTE
