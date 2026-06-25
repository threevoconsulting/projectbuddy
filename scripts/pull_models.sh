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

echo "==> Piper voice (TTS)"
VOICE_DIR="${PB_VOICE_DIR:-./models/piper}"
VOICE="${PB_PIPER_VOICE:-en_US-amy-medium}"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
mkdir -p "$VOICE_DIR"
if command -v curl >/dev/null 2>&1; then
  curl -L -o "$VOICE_DIR/$VOICE.onnx"      "$BASE/$VOICE.onnx"      || true
  curl -L -o "$VOICE_DIR/$VOICE.onnx.json" "$BASE/$VOICE.onnx.json" || true
  echo "   Voice at $VOICE_DIR/$VOICE.onnx"
  echo "   Set: export PB_PIPER_VOICE_PATH=$VOICE_DIR/$VOICE.onnx"
else
  echo "   curl not found — download a Piper voice manually from $BASE" >&2
fi

cat <<'NOTE'

==> faster-whisper (STT) model weights download automatically on first use
    (cached under ~/.cache/huggingface). Pick the size with PB_WHISPER_MODEL
    (tiny|base|small). See docs/running-on-mac.md.
NOTE
