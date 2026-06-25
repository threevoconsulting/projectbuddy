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


class PersonUpdate(BaseModel):
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


# --- Parent companion app (M9): read/manage surfaces ---
class SessionOut(BaseModel):
    id: int
    started_at: str
    ended_at: str | None = None
    summary: str | None = None


class MessageOut(BaseModel):
    id: int
    role: str  # "child" | "buddy"
    text: str
    emotion: str | None = None
    created_at: str


class PersonStatsOut(BaseModel):
    person_id: int
    session_count: int
    message_count: int
    fact_count: int
    created_at: str
    last_seen_at: str | None = None
    face_enrolled: bool
    face_consent: bool


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


# --- Perception (M7): face recognition + parental consent ---
# Images travel as base64 strings in JSON (no python-multipart dependency, and the
# capture UI in M9 will send frames the same way). Images are embedded in memory and
# discarded — they are never written to disk.
class ConsentSet(BaseModel):
    scope: str = Field(default="face", max_length=40)
    granted: bool
    granted_by: str | None = Field(default=None, max_length=200)
    retention_until: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=400)


class ConsentOut(BaseModel):
    person_id: int
    scope: str
    granted: bool
    granted_at: str | None = None
    granted_by: str | None = None
    retention_until: str | None = None


class EnrollRequest(BaseModel):
    # One or more base64-encoded capture frames, averaged into one stored embedding.
    images: list[str] = Field(min_length=1, max_length=20)


class EnrollResponse(BaseModel):
    person_id: int
    frames: int
    vector_size: int


class RecognizeRequest(BaseModel):
    image: str  # base64-encoded image


class RecognizeResponse(BaseModel):
    matched: bool
    person_id: int | None = None
    display_name: str | None = None
    role: str | None = None  # "child" | "parent" — lets the UI/greeting adapt
    confidence: float
    face_present: bool = False  # a face was detected (matched or not) vs an empty frame


class RetentionRunResponse(BaseModel):
    deleted_person_ids: list[int]
