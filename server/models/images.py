"""Making pictures on this PC."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from server.models.attachments import Attachment


class ImageModelOption(BaseModel):
    key: str
    display_name: str
    why: str
    license: str
    installed: bool


class ImageStatus(BaseModel):
    runtime: bool
    """stable-diffusion.cpp is on this PC."""
    model: str
    model_installed: bool
    ready: bool
    options: list[ImageModelOption]
    state: Literal["idle", "installing", "generating", "failed"] = "idle"
    detail: str = ""
    step: int = 0
    total: int = 0


class InstallRequest(BaseModel):
    model: str


class GenerateRequest(BaseModel):
    conversation_id: str
    prompt: str
    negative: str = ""
    seed: int | None = None


class Generated(BaseModel):
    conversation_id: str
    message_id: str
    attachment: Attachment
    seconds: float


class GalleryItem(BaseModel):
    """One picture you made: what you asked for, and the chat it lives in."""

    attachment_id: str
    conversation_id: str
    prompt: str
    created_at: int
