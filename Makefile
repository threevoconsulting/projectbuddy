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
run:
	uv run uvicorn projectbuddy.app:create_app --factory --reload --host 127.0.0.1 --port 8000

# Run on a Mac with the real models. Requires: uv sync --extra mac, Ollama running,
# and Piper/Whisper assets (see scripts/pull_models.sh and docs/running-on-mac.md).
run-mac:
	PB_LLM_BACKEND=ollama PB_STT_BACKEND=faster_whisper PB_TTS_BACKEND=piper \
		uv run uvicorn projectbuddy.app:create_app --factory --host 0.0.0.0 --port 8000

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache **/__pycache__
