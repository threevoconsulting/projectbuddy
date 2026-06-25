#!/usr/bin/env bash
# Run Buddy on a Mac with the REAL model stack.
# Prereqs: `uv sync --extra mac`, Ollama running, and Piper/Whisper assets
# (see scripts/pull_models.sh and docs/running-on-mac.md).
set -euo pipefail
cd "$(dirname "$0")/.."

export PB_LLM_BACKEND="${PB_LLM_BACKEND:-ollama}"
export PB_STT_BACKEND="${PB_STT_BACKEND:-faster_whisper}"
export PB_TTS_BACKEND="${PB_TTS_BACKEND:-piper}"
export PB_PIPER_VOICE_PATH="${PB_PIPER_VOICE_PATH:-}"
PB_HOST="${PB_HOST:-0.0.0.0}"
PB_PORT="${PB_PORT:-8765}"

if [[ "$PB_TTS_BACKEND" == "piper" && -z "$PB_PIPER_VOICE_PATH" ]]; then
  echo "   ! PB_PIPER_VOICE_PATH is unset — Piper needs a voice .onnx file." >&2
  echo "     Download one (see scripts/pull_models.sh) and export the path, or set" >&2
  echo "     PB_TTS_BACKEND=fake to run without a voice." >&2
fi

echo "==> Starting Buddy (LLM=$PB_LLM_BACKEND) on http://$PB_HOST:$PB_PORT  (face at /app/)"
uv run uvicorn projectbuddy.app:create_app --factory --host "$PB_HOST" --port "$PB_PORT"
