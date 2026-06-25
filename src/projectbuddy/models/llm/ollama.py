"""Ollama LLM adapter (real backend; runs on the household Mac).

Talks to the local Ollama server's ``/api/chat`` endpoint with ``format:"json"`` to
encourage a valid envelope, a small context window, and streaming disabled (the
parser needs the whole object). Kept dependency-light (raw httpx) so it is trivial
to stub with respx in wiring tests.
"""

from __future__ import annotations

import httpx

from projectbuddy.models.llm.base import ChatMessage


class OllamaLLMClient:
    def __init__(
        self,
        *,
        url: str,
        model: str,
        num_ctx: int = 4096,
        timeout: float = 30.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._model = model
        self._num_ctx = num_ctx
        self._client = httpx.AsyncClient(base_url=self._url, timeout=timeout)

    async def chat(self, messages: list[ChatMessage], *, json: bool = True) -> str:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": self._num_ctx},
        }
        if json:
            payload["format"] = "json"
        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return str(data["message"]["content"])

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
