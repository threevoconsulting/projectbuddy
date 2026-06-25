"""The face-recognition REST surface on the fakes (M7).

Covers the consent gate (no enroll without parent consent), the enroll→recognize
round-trip (the deterministic fake makes the same image match itself), and the error
paths (no face, unknown person, bad image).
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _make_person(client: TestClient, name: str = "Emma") -> int:
    return int(client.post("/person", json={"display_name": name, "role": "child"}).json()["id"])


def test_enroll_requires_consent(client: TestClient) -> None:
    pid = _make_person(client)
    r = client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"emma-face")]})
    assert r.status_code == 403


def test_consent_enroll_recognize_roundtrip(client: TestClient) -> None:
    pid = _make_person(client)

    # Parent grants face consent.
    c = client.post(
        f"/person/{pid}/consent",
        json={"scope": "face", "granted": True, "granted_by": "parent@example.com"},
    )
    assert c.status_code == 200 and c.json()["granted"] is True

    # Enroll succeeds now and stores one averaged embedding.
    e = client.post(
        f"/person/{pid}/enroll",
        json={"images": [_b64(b"emma-face-1"), _b64(b"emma-face-2")]},
    )
    assert e.status_code == 200
    body = e.json()
    assert body["person_id"] == pid and body["frames"] == 2 and body["vector_size"] == 512

    # Recognizing an enrolled frame matches the same person (fake is deterministic).
    r = client.post("/recognize", json={"image": _b64(b"emma-face-1")})
    assert r.status_code == 200
    rec = r.json()
    assert rec["matched"] is True and rec["person_id"] == pid and rec["confidence"] >= 0.6

    # An unknown face does not match.
    other = client.post("/recognize", json={"image": _b64(b"a-stranger")})
    assert other.json()["matched"] is False


def test_recognize_with_no_enrollments_returns_no_match(client: TestClient) -> None:
    r = client.post("/recognize", json={"image": _b64(b"anybody")})
    assert r.status_code == 200 and r.json()["matched"] is False


def test_enroll_with_no_face_is_400(client: TestClient) -> None:
    pid = _make_person(client)
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": True})
    # The fake returns no embedding for empty image bytes → "no face detected".
    r = client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"")]})
    assert r.status_code == 400


def test_consent_unknown_person_is_404(client: TestClient) -> None:
    r = client.post("/person/9999/consent", json={"scope": "face", "granted": True})
    assert r.status_code == 404


def test_revoke_blocks_enroll_again(client: TestClient) -> None:
    pid = _make_person(client)
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": True})
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": False})
    r = client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"emma-face")]})
    assert r.status_code == 403


def test_revoke_consent_deletes_face_template(client: TestClient) -> None:
    pid = _make_person(client)
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": True})
    client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"emma-face")]})
    assert client.post("/recognize", json={"image": _b64(b"emma-face")}).json()["matched"]

    # Revoking face consent must remove the stored template immediately.
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": False})
    assert client.post("/recognize", json={"image": _b64(b"emma-face")}).json()["matched"] is False


def test_retention_run_deletes_expired(client: TestClient) -> None:
    pid = _make_person(client)
    client.post(
        f"/person/{pid}/consent",
        json={"scope": "face", "granted": True, "retention_until": "2000-01-01"},
    )
    client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"emma-face")]})

    run = client.post("/retention/run")
    assert run.status_code == 200 and pid in run.json()["deleted_person_ids"]
    assert client.post("/recognize", json={"image": _b64(b"emma-face")}).json()["matched"] is False


def test_recognize_returns_display_name(client: TestClient) -> None:
    pid = _make_person(client, name="Ada")
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": True})
    client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"ada-face")]})
    rec = client.post("/recognize", json={"image": _b64(b"ada-face")}).json()
    assert rec["matched"] and rec["display_name"] == "Ada"


class _RejectAllLiveness:
    """Stand-in anti-spoof that flags everything as a spoof."""

    async def check(self, image: bytes) -> bool:
        return False


def test_liveness_failure_blocks_enroll(client: TestClient) -> None:
    pid = _make_person(client)
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": True})
    client.app.state.container.liveness = _RejectAllLiveness()
    r = client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"a-photo")]})
    assert r.status_code == 400 and r.json()["detail"] == "liveness check failed"


def test_liveness_failure_blocks_recognize(client: TestClient) -> None:
    pid = _make_person(client)
    client.post(f"/person/{pid}/consent", json={"scope": "face", "granted": True})
    client.post(f"/person/{pid}/enroll", json={"images": [_b64(b"emma-face")]})
    client.app.state.container.liveness = _RejectAllLiveness()
    rec = client.post("/recognize", json={"image": _b64(b"emma-face")}).json()
    assert rec["matched"] is False
