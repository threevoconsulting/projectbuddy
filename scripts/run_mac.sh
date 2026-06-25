#!/usr/bin/env bash
# Run Buddy on a Mac with the REAL model stack.
# Prereqs: `uv sync --extra mac`, Ollama running, and Piper/Whisper assets
# (see scripts/pull_models.sh and docs/running-on-mac.md).
set -euo pipefail
cd "$(dirname "$0")/.."

# Kokoro is the default voice — warm and natural (kinder for kids than Piper's more
# synthetic tone). Set PB_TTS_BACKEND=piper for the faster, lighter voice.
export PB_LLM_BACKEND="${PB_LLM_BACKEND:-ollama}"
export PB_STT_BACKEND="${PB_STT_BACKEND:-faster_whisper}"
export PB_TTS_BACKEND="${PB_TTS_BACKEND:-kokoro}"
export PB_RECOGNITION_BACKEND="${PB_RECOGNITION_BACKEND:-insightface}"
export PB_PIPER_VOICE_PATH="${PB_PIPER_VOICE_PATH:-./models/piper/en_US-amy-medium.onnx}"
PB_HOST="${PB_HOST:-0.0.0.0}"
PB_PORT="${PB_PORT:-8765}"

if [[ "$PB_TTS_BACKEND" == "piper" && -z "$PB_PIPER_VOICE_PATH" ]]; then
  echo "   ! PB_PIPER_VOICE_PATH is unset — Piper needs a voice .onnx file." >&2
  echo "     Download one (see scripts/pull_models.sh) and export the path, or set" >&2
  echo "     PB_TTS_BACKEND=fake to run without a voice." >&2
fi

# Serve over HTTPS when a cert exists (so a LAN tablet gets camera/mic). See make_cert.sh.
CERT="${PB_SSL_CERTFILE:-./certs/buddy.pem}"
KEY="${PB_SSL_KEYFILE:-./certs/buddy-key.pem}"
SSL_ARGS=()
SCHEME="http"
if [[ -f "$CERT" && -f "$KEY" ]]; then
  SSL_ARGS=(--ssl-certfile "$CERT" --ssl-keyfile "$KEY")
  SCHEME="https"
fi

echo "==> Starting Buddy (LLM=$PB_LLM_BACKEND) on $SCHEME://$PB_HOST:$PB_PORT  (face at /app/)"
uv run uvicorn projectbuddy.app:create_app --factory --host "$PB_HOST" --port "$PB_PORT" \
  ${SSL_ARGS[@]+"${SSL_ARGS[@]}"}
