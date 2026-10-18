"""What the updater knows, for the Settings row and the sidebar's "Restart to update"."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

UpdateState = Literal[
    "idle", "checking", "up_to_date", "available", "downloading", "ready", "installing", "failed"
]


class UpdateStatus(BaseModel):
    current: str
    state: UpdateState = "idle"
    latest: str = ""
    notes: str = ""
    """The release notes, as written on the release."""
    bytes_done: int = 0
    bytes_total: int = 0
    detail: str = ""
    auto: bool = True
    """Check once a day and fetch a new version in the background. Asks nothing of you but a
    restart, and sends nothing about you: it is one GET of a public file on GitHub."""
    can_install: bool = False
    """Only the installed Windows app can replace itself. A checkout updates with git."""
    checked_at: str = ""


class UpdatePrefs(BaseModel):
    auto: bool
