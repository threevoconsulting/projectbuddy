"""Permissive fake liveness detector — powers CI and the no-models dev stack.

Treats any non-empty frame as live, so the faked enroll/recognize flow is unaffected;
only truly empty input is rejected. Real anti-spoof lives in the MiniFASNet adapter.
"""

from __future__ import annotations


class FakeLivenessDetector:
    async def check(self, image: bytes) -> bool:
        return bool(image)
