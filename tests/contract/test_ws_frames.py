"""Contract for WS /ws/converse: frame ordering, face-leads-voice, and persistence.

Driven entirely on the fakes. The fake STT treats the audio bytes as the transcript,
so a test can "speak" by sending text; the fake LLM turns "dinosaurs" into an excited
reply with a remembered fact.
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient


def _say(ws: object, text: str) -> list[dict]:
    """Stream one utterance and collect server frames up to and including `final`."""
    chunk = base64.b64encode(text.encode("utf-8")).decode("ascii")
    ws.send_json({"type": "audio", "chunk": chunk})  # type: ignore[attr-defined]
    ws.send_json({"type": "end"})  # type: ignore[attr-defined]
    frames: list[dict] = []
    while True:
        frame = ws.receive_json()  # type: ignore[attr-defined]
        frames.append(frame)
        if frame["type"] == "final":
            return frames


def test_turn_frame_order_face_leads_voice(client: TestClient) -> None:
    with client.websocket_connect("/ws/converse") as ws:
        # On connect the server announces it is listening.
        assert ws.receive_json() == {"type": "state", "value": "listening"}

        frames = _say(ws, "I love dinosaurs!")
        types = [f["type"] for f in frames]

        # thinking → emotion → speaking → audio(s) → final
        assert types[0] == "state" and frames[0]["value"] == "thinking"
        assert "emotion" in types and "audio" in types and types[-1] == "final"

        # The face leads the voice: emotion precedes the `speaking` state, which in
        # turn precedes the first audio chunk.
        speaking = [
            i for i, f in enumerate(frames) if f["type"] == "state" and f["value"] == "speaking"
        ]
        assert speaking, "expected a speaking state frame"
        assert types.index("emotion") < speaking[0] < types.index("audio")

        # The transcript round-trips and the spoken line is non-empty.
        final = frames[-1]
        assert final["transcript"] == "I love dinosaurs!"
        assert final["say"]

        # After the turn the server returns to listening for the next utterance.
        assert ws.receive_json() == {"type": "state", "value": "listening"}


def test_unintelligible_input_is_handled_gently(client: TestClient) -> None:
    with client.websocket_connect("/ws/converse") as ws:
        assert ws.receive_json()["value"] == "listening"
        # End with no audio → empty transcript → gentle confused reply, no LLM turn.
        ws.send_json({"type": "end"})
        emotion = ws.receive_json()
        final = ws.receive_json()
        assert emotion == {"type": "emotion", "value": "confused"}
        assert final["type"] == "final" and final["transcript"] == ""


def test_audio_chunks_are_base64_pcm(client: TestClient) -> None:
    with client.websocket_connect("/ws/converse") as ws:
        ws.receive_json()  # listening
        frames = _say(ws, "tell me a joke")
        audio = [f for f in frames if f["type"] == "audio"]
        assert audio
        for f in audio:
            decoded = base64.b64decode(f["chunk"], validate=True)
            assert len(decoded) % 2 == 0  # 16-bit PCM
