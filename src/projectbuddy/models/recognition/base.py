"""The face-recognition seam (Phase 2a).

Buddy "sees" a family member only through :class:`FaceRecognizer`. The seam is
deliberately thin: the adapter's one job is to turn an image into a face embedding
(a fixed-length vector). Everything else — averaging several captures into one
enrolled vector, and matching a probe against enrolled vectors by cosine
similarity — is pure-Python logic in :mod:`projectbuddy.core.recognition`, so it is
fully testable with no models and never pulls in numpy on the CI path.

The fake adapter powers CI and the no-models dev container; the InsightFace adapter
(``buffalo_l``) runs on the household Mac. Selection is by env var
(``PB_RECOGNITION_BACKEND``) — see :mod:`projectbuddy.deps`.

Embeddings are plain ``list[float]`` (length :data:`EMBEDDING_DIM`); the repository
stores them as JSON so no binary/numpy dependency leaks into persistence.
"""

from __future__ import annotations

from typing import Protocol

EMBEDDING_DIM = 512  # ArcFace / buffalo_l embedding length


class FaceRecognizer(Protocol):
    async def embed(self, image: bytes) -> list[float] | None:
        """Return a face embedding for the largest face in ``image``.

        ``image`` is encoded bytes (JPEG/PNG). Returns ``None`` when no face is
        detected (or the input is empty), so callers can answer gently rather than
        enrolling/recognizing noise.
        """
        ...
