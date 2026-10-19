"""The morning briefing: what it covers, when it comes, and what it said."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SectionKey = Literal["markets", "home", "agents"]
Days = Literal["daily", "weekdays"]


class BriefingSettings(BaseModel):
    enabled: bool = False
    time: str = Field(default="07:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    """Local time, 24-hour."""
    days: Days = "weekdays"
    sections: list[SectionKey] = ["markets", "home", "agents"]
    speak: bool = False
    """Read it aloud when you open the app the first time after it is written."""
    next_at: int | None = None
    """From the live scheduler; ignored on write."""


class BriefingSection(BaseModel):
    key: SectionKey
    title: str
    facts: str
    """What was gathered, verbatim - the model writes from this and you can check it against it."""


class Briefing(BaseModel):
    id: str
    created_at: int
    title: str
    body: str
    sections: list[BriefingSection]
    conversation_id: str | None = None
    """The briefing is also a chat, so you can ask about it."""
    read_at: int | None = None
