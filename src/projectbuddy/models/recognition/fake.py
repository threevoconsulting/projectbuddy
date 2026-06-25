"""Deterministic fake face recognizer — powers CI and the no-models dev container.

It derives a stable pseudo-embedding from the image bytes via SHA-256, so the *same*
image always yields the *same* vector (enroll → recognize round-trips) while different
images yield near-orthogonal vectors (so non-matches stay non-matches). Pure-Python,
no numpy — safe to import anywhere.
"""

from __future__ import annotations

import hashlib

from projectbuddy.models.recognition.base import EMBEDDING_DIM


def _vector_from_bytes(image: bytes) -> list[float]:
    """Expand a digest of ``image`` into EMBEDDING_DIM deterministic floats in [-1, 1]."""
    out: list[float] = []
    seed = hashlib.sha256(image).digest()
    counter = 0
    while len(out) < EMBEDDING_DIM:
        block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        for b in block:
            out.append((b / 255.0) * 2.0 - 1.0)
            if len(out) == EMBEDDING_DIM:
                break
        counter += 1
    return out


class FakeRecognizer:
    async def embed(self, image: bytes) -> list[float] | None:
        if not image:
            return None
        return _vector_from_bytes(image)
