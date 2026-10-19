"""Images in a conversation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Attachment(BaseModel):
    id: str
    mime: str
    bytes: int
    source: Literal["upload", "screen"] = "upload"
    message_id: str | None = None
    created_at: int
    url: str
    """Where the page loads it from: /api/attachments/<id>, on this PC."""
