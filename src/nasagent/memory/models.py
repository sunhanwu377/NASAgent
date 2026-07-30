from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    summary: str | None = None
    summary_index: int = 0


class SessionMeta(BaseModel):
    session_id: str
    name: str
    created_at: datetime
    last_active_at: datetime
    message_count: int = 0


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class Preferences(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
