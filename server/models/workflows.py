"""Workflows by example: a draft you review before it becomes a scheduled agent, and how each one
has been doing."""

from __future__ import annotations

from pydantic import BaseModel


class DraftRequest(BaseModel):
    description: str


class JobDraft(BaseModel):
    name: str
    cron: str
    schedule: str
    """The cron read back in words."""
    schedule_found: bool
    """False when the words named no schedule and a default was filled in - the form says so."""
    prompt: str
    tools: list[str]
    note: str = ""
    """How it was drafted, in one line - e.g. that the model was unavailable."""


class JobStats(BaseModel):
    job_id: str
    runs: int
    ok: int
    failed: int
    waiting: int
    """Runs parked right now on your approval."""
    recent: list[str]
    """The last runs' statuses, oldest first, for the history strip."""
    last_finished_at: int | None = None
    avg_seconds: float | None = None
