"""Ollama LLM adapter (real backend; runs on the household Mac).

Talks to the local Ollama server's ``/api/chat`` endpoint with ``format:"json"`` to
encourage a valid envelope, a small context window, and streaming disabled (the
parser needs the whole object). Kept dependency-light (raw httpx) so it is trivial
to stub with respx in wiring tests.
"""

from __future__ import annotations

import json as _json
from collections.abc import AsyncIterator

import httpx

from projectbuddy.models.llm.base import ChatMessage

# Reasoning models emit a slow hidden "thinking" pass that delays/empties the JSON.
# We turn it off for them (Ollama errors if `think` is sent to a non-thinking model,
# so only set it for models we know support it).
_THINKING_MODELS = ("qwen3", "deepseek-r1", "qwq", "magistral", "r1")


def _is_thinking_model(model: str) -> bool:
    name = model.lower()
    return any(tag in name for tag in _THINKING_MODELS)


class OllamaLLMClient:
    def __init__(
        self,
        *,
        url: str,
        model: str,
        num_ctx: int = 2048,
        num_predict: int = 128,
        keep_alive: str = "30m",
        timeout: float = 60.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._model = model
        self._num_ctx = num_ctx
        self._num_predict = num_predict
        self._keep_alive = keep_alive
        self._thinking = _is_thinking_model(model)
        self._client = httpx.AsyncClient(base_url=self._url, timeout=timeout)

    def _payload(
        self, messages: list[ChatMessage], *, stream: bool, json: bool
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
            # keep_alive keeps the model resident; num_predict caps the (short) reply.
            "keep_alive": self._keep_alive,
            "options": {"num_ctx": self._num_ctx, "num_predict": self._num_predict},
        }
        if json:
            payload["format"] = "json"
        if self._thinking:
            payload["think"] = False  # skip the slow reasoning pass on reasoning models
        return payload

    async def chat(self, messages: list[ChatMessage], *, json: bool = True) -> str:
        resp = await self._client.post(
            "/api/chat", json=self._payload(messages, stream=False, json=json)
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["message"]["content"])

    async def chat_stream(
        self, messages: list[ChatMessage], *, json: bool = True
    ) -> AsyncIterator[str]:
        """Stream content deltas from Ollama's NDJSON response."""
        payload = self._payload(messages, stream=True, json=json)
        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                data = _json.loads(line)
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break

    async def warmup(self) -> None:
        """Send a tiny prompt so the model is resident before the first child turn."""
        try:
            await self.chat(
                [{"role": "user", "content": "Say the word ready as JSON."}],
                json=True,
            )
        except httpx.HTTPError:
            # Warmup is best-effort; a cold first turn is acceptable.
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
