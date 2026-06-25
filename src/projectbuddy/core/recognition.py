"""Pure-Python face-matching helpers (no numpy → safe on the CI path).

The recognition *seam* only produces embeddings; combining and comparing them lives
here so it is trivially unit-testable without any model. Averaging turns several
enrollment captures into one stable vector; cosine similarity scores a probe against
the enrolled vectors, and ``best_match`` picks the closest above a threshold.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

Vector = Sequence[float]


def average_vectors(vectors: Sequence[Vector]) -> list[float]:
    """Element-wise mean of equal-length vectors (the enrolled embedding)."""
    if not vectors:
        raise ValueError("cannot average an empty list of vectors")
    dim = len(vectors[0])
    if any(len(v) != dim for v in vectors):
        raise ValueError("all vectors must have the same length")
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def cosine(a: Vector, b: Vector) -> float:
    """Cosine similarity in [-1, 1]; 0.0 if either vector has zero magnitude."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def best_match(
    probe: Vector,
    enrolled: Sequence[tuple[int, Vector]],
    threshold: float,
) -> tuple[int | None, float]:
    """Return ``(person_id, score)`` of the closest enrolled vector at/above
    ``threshold``, else ``(None, best_score)``. ``best_score`` is the top similarity
    seen (for logging/telemetry), even when nothing clears the bar."""
    best_id: int | None = None
    best_score = 0.0
    for person_id, vector in enrolled:
        score = cosine(probe, vector)
        if score > best_score:
            best_score = score
            best_id = person_id
    if best_id is not None and best_score >= threshold:
        return best_id, best_score
    return None, best_score
