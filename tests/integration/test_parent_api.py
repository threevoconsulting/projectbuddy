"""Parent companion app REST surfaces (M9): sessions, transcripts, stats, edit, fact delete."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _person(client: TestClient, name: str = "Emma") -> int:
    return int(client.post("/person", json={"display_name": name, "role": "child"}).json()["id"])


def test_update_person(client: TestClient) -> None:
    pid = _person(client)
    r = client.put(f"/person/{pid}", json={"display_name": "Emma B.", "role": "kid"})
    assert r.status_code == 200 and r.json()["display_name"] == "Emma B."
    assert client.put("/person/9999", json={"display_name": "x", "role": None}).status_code == 404


def test_sessions_and_messages(client: TestClient) -> None:
    pid = _person(client)
    # Two turns create a session with child+buddy messages.
    sid = client.post("/session/start", json={"person_id": pid}).json()["session_id"]
    client.post("/converse-text", json={"text": "tell me a joke", "session_id": sid})

    sessions = client.get(f"/person/{pid}/sessions").json()
    assert len(sessions) == 1 and sessions[0]["id"] == sid

    msgs = client.get(f"/session/{sid}/messages").json()
    roles = [m["role"] for m in msgs]
    assert "child" in roles and "buddy" in roles
    assert client.get("/session/9999/messages").status_code == 404


def test_person_stats(client: TestClient) -> None:
    pid = _person(client)
    sid = client.post("/session/start", json={"person_id": pid}).json()["session_id"]
    client.post("/converse-text", json={"text": "I like dinosaurs", "session_id": sid})

    stats = client.get(f"/person/{pid}/stats").json()
    assert stats["session_count"] == 1
    assert stats["message_count"] >= 2
    assert stats["face_enrolled"] is False and stats["face_consent"] is False
    assert client.get("/person/9999/stats").status_code == 404


def test_delete_fact(client: TestClient) -> None:
    pid = _person(client)
    sid = client.post("/session/start", json={"person_id": pid}).json()["session_id"]
    # The fake LLM remembers "likes_dinosaurs" on a dinosaur turn.
    client.post("/converse-text", json={"text": "I love dinosaurs!", "session_id": sid})
    facts = client.get(f"/person/{pid}/facts").json()
    assert facts, "expected a remembered fact"

    fid = facts[0]["id"]
    assert client.delete(f"/person/{pid}/facts/{fid}").status_code == 204
    assert all(f["id"] != fid for f in client.get(f"/person/{pid}/facts").json())
    assert client.delete(f"/person/{pid}/facts/{fid}").status_code == 404
