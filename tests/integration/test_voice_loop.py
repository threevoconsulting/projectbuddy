"""The voice loop persists and remembers, just like the text loop — on the fakes.

The WS audio loop reuses the same orchestration as /converse-text, so a turn spoken
over the socket should leave the same durable trace (facts, sessions) the parent
transparency endpoints expose.
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient


def _speak(ws: object, text: str) -> dict:
    chunk = base64.b64encode(text.encode("utf-8")).decode("ascii")
    ws.send_json({"type": "audio", "chunk": chunk})  # type: ignore[attr-defined]
    ws.send_json({"type": "end"})  # type: ignore[attr-defined]
    while True:
        frame = ws.receive_json()  # type: ignore[attr-defined]
        if frame["type"] == "final":
            return frame


def test_voice_turn_remembers_and_is_resumable(client: TestClient) -> None:
    with client.websocket_connect("/ws/converse") as ws:
        ws.receive_json()  # initial listening
        _speak(ws, "I love dinosaurs!")
        ws.receive_json()  # trailing listening

    # The default person gained the remembered fact via the spoken turn.
    people = client.get("/person").json()
    assert len(people) == 1
    pid = people[0]["id"]
    facts = client.get(f"/person/{pid}/facts").json()
    assert any(f["key"] == "likes_dinosaurs" for f in facts)


def test_voice_turns_continue_one_session(client: TestClient) -> None:
    with client.websocket_connect("/ws/converse") as ws:
        ws.receive_json()
        _speak(ws, "hello")
        ws.receive_json()
        _speak(ws, "tell me a story")
        ws.receive_json()

    # Both utterances landed in a single session for the one default person.
    container = client.app.state.container
    pid = client.get("/person").json()[0]["id"]
    sessions = container.db.query_all("SELECT id FROM session WHERE person_id = ?", (pid,))
    assert len(sessions) == 1
    messages = container.db.query_all(
        "SELECT role FROM message WHERE session_id = ?", (sessions[0]["id"],)
    )
    # Two child turns + two Buddy replies all in the one session.
    assert sum(1 for m in messages if m["role"] == "child") == 2
    assert sum(1 for m in messages if m["role"] == "buddy") == 2
