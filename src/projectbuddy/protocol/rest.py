"""Request/response models for the REST management API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from projectbuddy.protocol.llm_envelope import BuddyReply


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


# --- /converse-text (M1/M2: the text-only loop, no audio) ---
class ConverseTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None


class ConverseTextResponse(BaseModel):
    reply: BuddyReply
    session_id: int | None = None


# --- /person ---
class PersonCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    role: str | None = Field(default=None, max_length=40)


class PersonOut(BaseModel):
    id: int
    display_name: str
    role: str | None = None
    created_at: str
    last_seen_at: str | None = None


class FactOut(BaseModel):
    id: int
    key: str
    value: str
    confidence: float
    updated_at: str


# --- /session ---
class SessionStartRequest(BaseModel):
    person_id: int | None = None


class SessionStartResponse(BaseModel):
    session_id: int
    person_id: int
    resume_summary: str | None = None  # medium-term memory for "pick up where we left off"


class SessionEndRequest(BaseModel):
    session_id: int


class SessionEndResponse(BaseModel):
    session_id: int
    summary: str | None = None
