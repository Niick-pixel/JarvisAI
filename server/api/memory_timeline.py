"""The memory timeline: where each memory came from, where it has been used since, and taking it
back - one memory, or everything a chat taught - with an undo that puts the file back as it was.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from server.api.memory import ForgetResult
from server.deps import State
from server.errors import NotFound
from server.knowledge import memory, memory_git, memory_index
from server.models.memory import MemoryEntry

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryUse(BaseModel):
    """One chat this memory was put in front of the model, most recent use first."""

    conversation_id: str
    title: str
    times: int
    last_used_at: int


@router.get("/{entry_id}/uses")
def uses(entry_id: str, state: State) -> list[MemoryUse]:
    with state.db.session() as conn:
        if memory_index.get(conn, entry_id) is None:
            raise NotFound("Memory entry")
        rows = conn.execute(
            "SELECT c.id AS conversation_id, c.title AS title, COUNT(*) AS times,"
            " MAX(u.used_at) AS last_used_at FROM memory_usage u"
            " JOIN messages m ON m.id = u.message_id"
            " JOIN conversations c ON c.id = m.conversation_id"
            " WHERE u.entry_id = ? GROUP BY c.id ORDER BY last_used_at DESC LIMIT 20",
            (entry_id,),
        )
        return [MemoryUse(**dict(r)) for r in rows]


@router.delete("/from-conversation/{conversation_id}")
def forget_chat(conversation_id: str, state: State) -> list[MemoryEntry]:
    """Forget everything one chat taught. Returns what went, so the client can offer undo."""
    root = state.settings.paths.memory_dir
    with state.db.session() as conn:
        taught = [
            e for e in memory_index.list_all(conn) if e.source_conversation_id == conversation_id
        ]
        for entry in taught:
            memory.delete(root, entry.path)
        if taught:
            memory_git.commit(root, f"memory: forget {len(taught)} learned in {conversation_id}")
            memory_index.sync(conn, root)
    return taught


@router.post("/restore")
def restore(entries: list[MemoryEntry], state: State) -> ForgetResult:
    """Undo a forget: the same facts, ids and origins written back as files."""
    root = state.settings.paths.memory_dir
    for entry in entries:
        memory.write(root, entry.model_copy(update={"path": ""}))
    with state.db.session() as conn:
        if entries:
            memory_git.commit(root, f"memory: restore {len(entries)}")
        remaining = memory_index.sync(conn, root)
    return ForgetResult(forgotten="", remaining=remaining)
