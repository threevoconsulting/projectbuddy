"""Pure-Python matching helpers + the deterministic fake recognizer (M7)."""

from __future__ import annotations

import math

import pytest

from projectbuddy.core.recognition import average_vectors, best_match, cosine
from projectbuddy.models.recognition.base import EMBEDDING_DIM
from projectbuddy.models.recognition.fake import FakeRecognizer


def test_cosine_identical_and_orthogonal() -> None:
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_zero_vector_is_zero() -> None:
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_average_vectors() -> None:
    assert average_vectors([[0.0, 2.0], [2.0, 0.0]]) == [1.0, 1.0]
    with pytest.raises(ValueError):
        average_vectors([])
    with pytest.raises(ValueError):
        average_vectors([[1.0], [1.0, 2.0]])


def test_best_match_picks_closest_above_threshold() -> None:
    enrolled = [(1, [1.0, 0.0]), (2, [0.0, 1.0])]
    pid, score = best_match([0.9, 0.1], enrolled, threshold=0.6)
    assert pid == 1 and score > 0.6


def test_best_match_returns_none_below_threshold() -> None:
    enrolled = [(1, [1.0, 0.0])]
    pid, score = best_match([0.0, 1.0], enrolled, threshold=0.6)
    assert pid is None
    assert score == pytest.approx(0.0)


def test_best_match_empty_enrollment() -> None:
    assert best_match([1.0, 0.0], [], threshold=0.6) == (None, 0.0)


async def test_fake_recognizer_is_deterministic_and_sized() -> None:
    rec = FakeRecognizer()
    v1 = await rec.embed(b"a face")
    v2 = await rec.embed(b"a face")
    other = await rec.embed(b"different face")
    assert v1 is not None and v2 is not None and other is not None
    assert len(v1) == EMBEDDING_DIM
    assert v1 == v2  # same image → same vector (enroll/recognize round-trips)
    # Same image matches itself; a different image does not (near-orthogonal).
    assert cosine(v1, v2) == pytest.approx(1.0)
    assert cosine(v1, other) < 0.6


async def test_fake_recognizer_no_face_on_empty() -> None:
    assert await FakeRecognizer().embed(b"") is None


async def test_fake_vectors_have_nonzero_magnitude() -> None:
    # Sanity: vectors have non-zero magnitude so cosine is well-defined.
    v = await FakeRecognizer().embed(b"x")
    assert v is not None
    assert math.sqrt(sum(x * x for x in v)) > 0
