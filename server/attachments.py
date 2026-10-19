"""Images in a conversation: stored as files, linked to the message they were sent with, and
handed to a model that can see as base64 data URLs.

Only real images are accepted - the first bytes are checked, not the name or the header the
browser claimed - because these bytes go straight into a model's input.
"""

from __future__ import annotations

import base64
import sqlite3
from pathlib import Path

from server.ids import new_id, now_ms
from server.models.attachments import Attachment

MAX_BYTES = 12 * 1024 * 1024
MAX_VIDEO_BYTES = 80 * 1024 * 1024
"""A generated clip. Never an upload: only Jarvis's own video model writes these."""
MAGIC = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}
EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "video/webm": "webm",
}


def sniff(data: bytes) -> str | None:
    for magic, mime in MAGIC.items():
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"\x1a\x45\xdf\xa3":  # EBML: the start of every WebM file
        return "video/webm"
    return None


def folder(data_dir: Path) -> Path:
    return data_dir / "attachments"


def path_for(data_dir: Path, attachment_id: str, mime: str) -> Path:
    return folder(data_dir) / f"{attachment_id}.{EXT.get(mime, 'bin')}"


def _row(row: sqlite3.Row) -> Attachment:
    data = {k: row[k] for k in ("id", "mime", "bytes", "source", "message_id", "created_at")}
    return Attachment(**data, url=f"/api/attachments/{row['id']}")


def save(
    conn: sqlite3.Connection,
    data_dir: Path,
    data: bytes,
    *,
    source: str = "upload",
    conversation_id: str | None = None,
) -> Attachment:
    mime = sniff(data)
    if mime is None or (mime.startswith("video/") and source != "generated"):
        raise ValueError("That is not a PNG, JPEG, GIF or WebP image.")
    if mime.startswith("video/") and len(data) > MAX_VIDEO_BYTES:
        raise ValueError("That clip is too large to keep.")
    if not mime.startswith("video/") and len(data) > MAX_BYTES:
        raise ValueError(f"Images up to {MAX_BYTES // (1024 * 1024)} MB.")
    attachment_id = new_id("att")
    target = path_for(data_dir, attachment_id, mime)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    conn.execute(
        "INSERT INTO attachments (id, conversation_id, mime, bytes, source, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (attachment_id, conversation_id, mime, len(data), source, now_ms()),
    )
    row = conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
    return _row(row)


def get(conn: sqlite3.Connection, attachment_id: str) -> Attachment | None:
    row = conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
    return _row(row) if row else None


def link(conn: sqlite3.Connection, ids: list[str], conversation_id: str, message_id: str) -> None:
    """Attach uploads to the message they were sent with. Ones already sent elsewhere stay put."""
    conn.executemany(
        "UPDATE attachments SET message_id = ?, conversation_id = ?"
        " WHERE id = ? AND message_id IS NULL",
        [(message_id, conversation_id, i) for i in ids],
    )


def for_conversation(conn: sqlite3.Connection, conversation_id: str) -> dict[str, list[Attachment]]:
    rows = conn.execute(
        "SELECT * FROM attachments WHERE conversation_id = ? AND message_id IS NOT NULL"
        " ORDER BY created_at",
        (conversation_id,),
    ).fetchall()
    out: dict[str, list[Attachment]] = {}
    for row in rows:
        out.setdefault(row["message_id"], []).append(_row(row))
    return out


def data_url(data_dir: Path, attachment: Attachment) -> str:
    raw = path_for(data_dir, attachment.id, attachment.mime).read_bytes()
    return f"data:{attachment.mime};base64,{base64.b64encode(raw).decode()}"


def images_for(
    conn: sqlite3.Connection, data_dir: Path, conversation_id: str
) -> dict[str, list[str]]:
    """Each message's images as data URLs, for the prompt."""
    return {
        message_id: [
            data_url(data_dir, a)
            for a in found
            # A clip is not a picture: a vision model gets only the images.
            if a.mime.startswith("image/") and path_for(data_dir, a.id, a.mime).is_file()
        ]
        for message_id, found in for_conversation(conn, conversation_id).items()
    }
