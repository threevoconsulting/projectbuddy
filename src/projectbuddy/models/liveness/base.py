"""The liveness / anti-spoof seam (deferred from M8).

A thin gate in front of enrollment and recognition: given an encoded image, decide
whether it is a *live* face rather than a photo/screen replay. Like every model seam,
a ``fake`` adapter powers CI (permissive) and a real adapter (MiniFASNet via ONNX) runs
on the Mac, selected by ``PB_LIVENESS_BACKEND``.
"""

from __future__ import annotations

from typing import Protocol


class LivenessDetector(Protocol):
    async def check(self, image: bytes) -> bool:
        """Return True if ``image`` looks like a live face, False for empty/spoofed input."""
        ...
