from __future__ import annotations

from projectbuddy.core.memory import MemoryManager
from projectbuddy.db.engine import Database
from projectbuddy.db.repositories import FactRepo, MessageRepo, PersonRepo, SessionRepo
from projectbuddy.protocol.llm_envelope import BuddyReply, Emotion, Fact


def _memory(db: Database) -> tuple[MemoryManager, int, int]:
    persons = PersonRepo(db)
    facts = FactRepo(db)
    sessions = SessionRepo(db)
    messages = MessageRepo(db)
    mem = MemoryManager(facts=facts, sessions=sessions, messages=messages, short_term_turns=4)
    p = persons.create("Emma")
    s = sessions.start(p.id)
    return mem, p.id, s.id


def test_build_context_starts_with_system_prompt(db: Database) -> None:
    mem, pid, sid = _memory(db)
    ctx = mem.build_context(person_id=pid, session_id=sid, child_text="hi")
    assert ctx[0]["role"] == "system"
    assert ctx[-1] == {"role": "user", "content": "hi"}


def test_build_context_includes_facts_and_summary(db: Database) -> None:
    mem, pid, sid = _memory(db)
    mem.commit_turn(
        person_id=pid,
        session_id=sid,
        child_text="my favorite dino is the stegosaurus",
        reply=BuddyReply(
            emotion=Emotion.excited,
            say="Cool!",
            remember=[Fact(key="favorite_dino", value="stegosaurus")],
        ),
    )
    ctx = mem.build_context(person_id=pid, session_id=sid, child_text="more please")
    system = ctx[0]["content"]
    assert "favorite_dino" in system
    assert "stegosaurus" in system


def test_short_term_window_is_bounded(db: Database) -> None:
    mem, pid, sid = _memory(db)  # short_term_turns=4
    for i in range(10):
        mem._messages.add(sid, "child", f"line {i}")
    ctx = mem.build_context(person_id=pid, session_id=sid, child_text="now")
    # system + last 4 messages + the new user line
    assert len(ctx) == 1 + 4 + 1


def test_summarize_session(db: Database) -> None:
    mem, _pid, sid = _memory(db)
    mem._messages.add(sid, "child", "tell me about space")
    mem._messages.add(sid, "buddy", "rockets!", emotion="excited")
    summary = mem.summarize_session(sid)
    assert summary is not None
    assert "space" in summary
