"""The LLM seam.

Buddy's brain is reached only through :class:`LLMClient`. The fake adapter powers
CI and the cloud dev container; the Ollama adapter runs on the household Mac. The
orchestrator and parser depend on this Protocol, never on a concrete backend.
"""

from __future__ import annotations

from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(Protocol):
    async def chat(self, messages: list[ChatMessage], *, json: bool = True) -> str:
        """Return the assistant's raw text reply.

        When ``json`` is true the backend is asked to constrain output to a JSON
        object (Buddy's structured envelope). Validation happens in the parser,
        not here — this returns the raw string.
        """
        ...

    async def warmup(self) -> None:
        """Optionally pre-load/warm the model to protect first-token latency."""
        ...
