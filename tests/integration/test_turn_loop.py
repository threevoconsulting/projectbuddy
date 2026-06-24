"""Full text turn loop on the fakes: child text in → validated reply out → persisted,
remembered, resumable, and forgettable. The M4 audio loop reuses this orchestration."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_turn_persists_and_remembers_across_session(client: TestClient) -> None:
    # A turn that the fake LLM turns into a remembered fact.
    r1 = client.post("/converse-text", json={"text": "I love dinosaurs!"})
    assert r1.status_code == 200
    session_id = r1.json()["session_id"]

    # The default person now has the fact, visible via the parent transparency endpoint.
    people = client.get("/person").json()
    assert len(people) == 1
    pid = people[0]["id"]
    facts = client.get(f"/person/{pid}/facts").json()
    assert any(f["key"] == "likes_dinosaurs" for f in facts)

    # Ending the session writes a resume summary…
    end = client.post("/session/end", json={"session_id": session_id}).json()
    assert end["summary"] and "dinosaurs" in end["summary"].lower()

    # …which the next /session/start hands back for "pick up where we left off".
    start = client.post("/session/start", json={"person_id": pid}).json()
    assert start["resume_summary"] is not None

    # "Forget" wipes everything for the person.
    assert client.delete(f"/person/{pid}").status_code == 204
    assert client.get(f"/person/{pid}/facts").status_code == 404


def test_second_turn_reuses_session(client: TestClient) -> None:
    r1 = client.post("/converse-text", json={"text": "hello"}).json()
    sid = r1["session_id"]
    r2 = client.post("/converse-text", json={"text": "tell me a joke", "session_id": sid}).json()
    assert r2["session_id"] == sid
