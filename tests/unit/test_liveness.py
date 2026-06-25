"""The fake liveness detector is permissive (keeps the faked stack working)."""

from __future__ import annotations

from projectbuddy.models.liveness.fake import FakeLivenessDetector


async def test_fake_liveness_accepts_a_frame_rejects_empty() -> None:
    detector = FakeLivenessDetector()
    assert await detector.check(b"a-real-frame") is True
    assert await detector.check(b"") is False
