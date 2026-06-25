"""Memory manager — the three tiers from the TDD.

* **Short-term:** the most recent turns of the current session, kept verbatim in the
  prompt (``short_term_turns``).
* **Medium-term:** a per-session ``summary`` written at session end, so the next
  session can resume ("let's pick up where we left off").
* **Long-term:** durable ``fact`` rows (preferences/details) persisted from the
  model's ``remember[]`` and injected into the prompt.

``build_context`` assembles the message list sent to the LLM; ``commit_turn``
persists a completed exchange; ``summarize_session`` writes the medium-term summary.
"""

from __future__ import annotations

from pathlib import Path

from projectbuddy.db.repositories import FactRepo, MessageRepo, SessionRepo
from projectbuddy.models.llm.base import ChatMessage
from projectbuddy.protocol.llm_envelope import BuddyReply

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_PATH = _PROJECT_ROOT / "config" / "system_prompt.md"

_FALLBACK_PROMPT = (
    "You are Buddy, a kind, curious, playful robot friend for a young child. "
    "Speak warmly and briefly. Reply with ONLY a JSON object: "
    '{"emotion": one of [happy, curious, thinking, excited, confused, sleepy, sad, '
    'celebrating], "say": short text, "remember": list}.'
)


def load_system_prompt() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return _FALLBACK_PROMPT


class MemoryManager:
    def __init__(
        self,
        *,
        facts: FactRepo,
        sessions: SessionRepo,
        messages: MessageRepo,
        short_term_turns: int = 12,
    ) -> None:
        self._facts = facts
        self._sessions = sessions
        self._messages = messages
        self._short_term_turns = short_term_turns
        self._system_prompt = load_system_prompt()

    def resume_summary(self, person_id: int) -> str | None:
        """Latest medium-term summary for a person (used at /session/start)."""
        return self._sessions.latest_summary(person_id)

    def build_context(
        self, *, person_id: int, session_id: int, child_text: str
    ) -> list[ChatMessage]:
        """Assemble the LLM message list: system + memory + recent turns + new input."""
        system_parts = [self._system_prompt]

        facts = self._facts.list(person_id)
        if facts:
            fact_lines = "; ".join(f"{f.key}: {f.value}" for f in facts)
            system_parts.append(f"Things you remember about this child: {fact_lines}.")

        summary = self._sessions.latest_summary(person_id)
        if summary:
            system_parts.append(f"Last time you talked about: {summary}")

        messages: list[ChatMessage] = [{"role": "system", "content": "\n\n".join(system_parts)}]

        for m in self._messages.recent(session_id, self._short_term_turns):
            role = "user" if m.role == "child" else "assistant"
            messages.append({"role": role, "content": m.text})

        messages.append({"role": "user", "content": child_text})
        return messages

    def build_greeting_context(
        self, *, person_id: int, session_id: int, display_name: str | None
    ) -> list[ChatMessage]:
        """Assemble the LLM messages for an arrival greeting (M8 continuity).

        Reuses the same system + memory + recent-turns context, then asks Buddy to
        greet the recognized child warmly by name — drawing on what it remembers.
        """
        name = display_name or "your friend"
        instruction = (
            f"[{name} just walked up and is looking at you.] Greet them warmly by name "
            "in one short, happy sentence. If you remember something they like, mention "
            "it kindly. Do not ask them to repeat anything."
        )
        return self.build_context(
            person_id=person_id, session_id=session_id, child_text=instruction
        )

    def commit_buddy_line(self, *, session_id: int, reply: BuddyReply) -> None:
        """Persist only Buddy's line (used by greetings, which have no child turn)."""
        self._messages.add(session_id, "buddy", reply.say, emotion=reply.emotion.value)

    def commit_turn(
        self, *, person_id: int, session_id: int, child_text: str, reply: BuddyReply
    ) -> None:
        """Persist the child's line, Buddy's line, and any remembered facts."""
        self._messages.add(session_id, "child", child_text)
        self._messages.add(session_id, "buddy", reply.say, emotion=reply.emotion.value)
        for fact in reply.remember:
            self._facts.upsert(person_id, fact.key, fact.value)

    def summarize_session(self, session_id: int) -> str | None:
        """Build a short medium-term summary from the session's child turns.

        Deterministic (no model needed) so it works in CI and is easy to test. A
        richer LLM-based summary can replace this behind the same method later.
        """
        msgs = self._messages.recent(session_id, limit=200)
        child_lines = [m.text.strip() for m in msgs if m.role == "child" and m.text.strip()]
        if not child_lines:
            return None
        snippets = child_lines[-5:]
        return "We talked about: " + " | ".join(snippets)
