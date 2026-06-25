.PHONY: setup lint format types test redteam run run-mac clean

# Dev setup — fakes only, no model runtimes. Fast and CI-safe.
setup:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

types:
	uv run mypy

test:
	uv run pytest

redteam:
	uv run python scripts/redteam.py

# Run the backend with the fully-faked stack (no models needed).
# Override host/port via env, e.g. `PB_PORT=9000 make run`.
run:
	uv run uvicorn projectbuddy.app:create_app --factory --reload --host $${PB_HOST:-127.0.0.1} --port $${PB_PORT:-8765}

# Run on a Mac with the real models. Requires: uv sync --extra mac --extra perception,
# Ollama running, and Piper/Whisper assets (see scripts/pull_models.sh and
# docs/running-on-mac.md). Enables the real recognizer too (PB_RECOGNITION_BACKEND).
run-mac:
	PB_LLM_BACKEND=ollama PB_STT_BACKEND=faster_whisper PB_TTS_BACKEND=piper \
	PB_RECOGNITION_BACKEND=insightface \
		uv run uvicorn projectbuddy.app:create_app --factory --host $${PB_HOST:-0.0.0.0} --port $${PB_PORT:-8765}

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache **/__pycache__
