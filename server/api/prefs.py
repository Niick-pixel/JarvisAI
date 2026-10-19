"""Your preferences - name, theme, how you like answers - kept in the database with everything else.

The window's own storage is a cache, not the record: a webview can be cleared, run privately, or
be a different origin next launch, and none of that should make Jarvis forget your name.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from server.db import repo
from server.deps import State
from server.errors import SovereignError

router = APIRouter(prefix="/api/prefs", tags=["prefs"])
KEY = "ui_prefs"
MAX_KEYS = 64


@router.get("")
def read(state: State) -> dict[str, Any]:
    with state.db.session() as conn:
        saved = repo.settings.get(conn, KEY)
    return saved if isinstance(saved, dict) else {}


@router.put("")
def merge(state: State, changes: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
    with state.db.session() as conn:
        saved = repo.settings.get(conn, KEY)
        merged = {**(saved if isinstance(saved, dict) else {}), **changes}
        if len(merged) > MAX_KEYS:
            raise SovereignError("invalid_request", "Too many preferences.")
        repo.settings.put(conn, KEY, merged)
    return merged
