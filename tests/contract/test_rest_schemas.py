from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_person_crud_and_facts(client: TestClient) -> None:
    created = client.post("/person", json={"display_name": "Emma", "role": "child"})
    assert created.status_code == 201
    pid = created.json()["id"]

    listed = client.get("/person")
    assert any(p["id"] == pid for p in listed.json())

    facts = client.get(f"/person/{pid}/facts")
    assert facts.status_code == 200
    assert facts.json() == []

    missing = client.get("/person/99999/facts")
    assert missing.status_code == 404


def test_session_start_end(client: TestClient) -> None:
    start = client.post("/session/start", json={})
    assert start.status_code == 200
    body = start.json()
    assert body["resume_summary"] is None
    sid = body["session_id"]

    end = client.post("/session/end", json={"session_id": sid})
    assert end.status_code == 200
    assert end.json()["session_id"] == sid


def test_converse_text_shape(client: TestClient) -> None:
    resp = client.post("/converse-text", json={"text": "tell me about space rockets"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"]["emotion"] in {
        "happy",
        "curious",
        "thinking",
        "excited",
        "confused",
        "sleepy",
        "sad",
        "celebrating",
    }
    assert isinstance(body["reply"]["say"], str) and body["reply"]["say"]
    assert isinstance(body["session_id"], int)
