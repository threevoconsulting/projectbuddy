#!/usr/bin/env bash
# Run Buddy on a Mac with the REAL model stack.
# Prereqs: `uv sync --extra mac`, Ollama running, and Piper/Whisper assets
# (see scripts/pull_models.sh and docs/running-on-mac.md).
set -euo pipefail
cd "$(dirname "$0")/.."

export PB_LLM_BACKEND="${PB_LLM_BACKEND:-ollama}"
export PB_STT_BACKEND="${PB_STT_BACKEND:-faster_whisper}"   # wired in M4
export PB_TTS_BACKEND="${PB_TTS_BACKEND:-piper}"            # wired in M4

echo "==> Starting Buddy (LLM=$PB_LLM_BACKEND) on http://0.0.0.0:8000  (face at /app/)"
uv run uvicorn projectbuddy.app:create_app --factory --host 0.0.0.0 --port 8000
