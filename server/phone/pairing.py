"""Pairing a phone: a six-digit code shown on this PC, traded once for a long-lived device token.

The code lasts five minutes and allows five tries, then a new one is needed - six digits are
guessable without that. The token is 32 random bytes; only its sha256 is stored, so the database
alone cannot sign anyone in. Revoking a device deletes its row, and its next request is refused.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass

from server.ids import new_id, now_ms
from server.models.phone import PairedDevice

CODE_TTL_S = 300
MAX_TRIES = 5
COOKIE = "jarvis_device"


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class Code:
    value: str
    expires_at: float
    tries: int = 0

    def live(self) -> bool:
        return time.time() < self.expires_at and self.tries < MAX_TRIES


class Pairing:
    def __init__(self) -> None:
        self.code: Code | None = None

    def new_code(self) -> Code:
        self.code = Code(f"{secrets.randbelow(10**6):06d}", time.time() + CODE_TTL_S)
        return self.code

    def current(self) -> Code | None:
        return self.code if self.code and self.code.live() else None

    def redeem(self, conn: sqlite3.Connection, attempt: str, name: str) -> str | None:
        """A device token for the right code, once. None for a wrong, used or expired code."""
        code = self.current()
        if code is None:
            return None
        code.tries += 1
        if not secrets.compare_digest(attempt.strip(), code.value):
            return None
        self.code = None  # one code, one phone
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO paired_devices (id, name, token_hash, created_at) VALUES (?,?,?,?)",
            (new_id("dev"), (name.strip() or "Phone")[:40], digest(token), now_ms()),
        )
        return token


def device_for(conn: sqlite3.Connection, token: str) -> str | None:
    row = conn.execute(
        "SELECT id FROM paired_devices WHERE token_hash = ?", (digest(token),)
    ).fetchone()
    if row is None:
        return None
    conn.execute("UPDATE paired_devices SET last_seen = ? WHERE id = ?", (now_ms(), row["id"]))
    return str(row["id"])


def devices(conn: sqlite3.Connection) -> list[PairedDevice]:
    rows = conn.execute("SELECT * FROM paired_devices ORDER BY created_at").fetchall()
    return [
        PairedDevice(**{k: r[k] for k in ("id", "name", "created_at", "last_seen")}) for r in rows
    ]


def revoke(conn: sqlite3.Connection, device_id: str) -> None:
    conn.execute("DELETE FROM paired_devices WHERE id = ?", (device_id,))
