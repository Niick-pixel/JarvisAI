"""What Jarvis keeps on this PC, how big it is, and wiping it - one kind at a time or all of it.

Each kind is removed the same way the app removes one of them anywhere else (memories through the
memory files and their history, knowledge through its sources), so nothing is left half-indexed.
Your own documents and folders are never touched: Knowledge and Files only ever read them.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from server.deps import AppState
from server.knowledge import memory, memory_git, memory_index

Kind = Literal["chats", "memory", "knowledge", "cache", "models", "everything"]
MODEL_FILES = ("*.gguf", "*.mmproj", "*.part")
KEEP_TABLES = {"schema_migrations", "models"}
"""Never emptied by "everything": the schema's own bookkeeping, and the list of downloaded models
(which have their own button, because they are gigabytes to fetch again)."""


class DataKind(BaseModel):
    kind: Kind
    count: int
    """Chats, memories, folders or model files - whatever this kind counts in."""
    bytes: int


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608


def _cache_paths(state: AppState) -> list[Path]:
    data = state.settings.paths.data_dir
    return [data / "updates", data / "files-backups", data / "llama-server.log"]


def _model_files(state: AppState) -> list[Path]:
    root = state.settings.paths.models_dir
    files = [p for pattern in MODEL_FILES for p in root.glob(pattern)]
    return files + [root / "images", root / "sdcpp"]


def usage(state: AppState) -> list[DataKind]:
    data = state.settings.paths.data_dir
    with state.db.session() as conn:
        chats, memories, sources = (
            _count(conn, t) for t in ("conversations", "memory_entries", "sources")
        )
    return [
        DataKind(kind="chats", count=chats, bytes=_size(data / "attachments")),
        DataKind(kind="memory", count=memories, bytes=_size(state.settings.paths.memory_dir)),
        DataKind(kind="knowledge", count=sources, bytes=0),
        DataKind(kind="cache", count=0, bytes=sum(_size(p) for p in _cache_paths(state))),
        DataKind(
            kind="models",
            count=len([p for p in _model_files(state) if p.is_file()]),
            bytes=sum(_size(p) for p in _model_files(state)),
        ),
    ]


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)


def clear_chats(state: AppState) -> None:
    with state.db.session() as conn:
        conn.execute("DELETE FROM conversations")
    _remove(state.settings.paths.data_dir / "attachments")


def clear_memory(state: AppState) -> None:
    root = state.settings.paths.memory_dir
    with state.db.session() as conn:
        entries = memory_index.list_all(conn)
        for entry in entries:
            memory.delete(root, entry.path)
        if entries:
            memory_git.commit(root, f"memory: forget all {len(entries)}")
        memory_index.sync(conn, root)


def clear_knowledge(state: AppState) -> None:
    state.watcher.stop_all()
    with state.db.session() as conn:
        conn.execute("DELETE FROM sources")
        # Created on first index, so it may not exist yet.
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'vec_chunks'").fetchone():
            conn.execute("DELETE FROM vec_chunks")


def clear_cache(state: AppState) -> None:
    for path in _cache_paths(state):
        _remove(path)


async def clear_models(state: AppState) -> None:
    # The running model holds its file open; on Windows a held file cannot be deleted.
    if state.llama is not None:
        await state.llama.stop()
    for path in _model_files(state):
        _remove(path)
    with state.db.session() as conn:
        conn.execute("DELETE FROM models")


def clear_everything(state: AppState) -> None:
    """Back to a fresh install, except the downloaded models."""
    clear_memory(state)
    clear_knowledge(state)
    clear_cache(state)
    _remove(state.settings.paths.data_dir / "attachments")
    for name in ("home.json", "files.json"):
        _remove(state.settings.paths.data_dir / name)
    with state.db.session() as conn:
        rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table'").fetchall()
        virtual = [r["name"] for r in rows if (r["sql"] or "").upper().startswith("CREATE VIRTUAL")]
        # A virtual table's shadow tables are emptied through it, never directly.
        tables = [
            r["name"]
            for r in rows
            if r["name"] not in KEEP_TABLES
            and not r["name"].startswith("sqlite_")
            and not any(r["name"].startswith(f"{v}_") for v in virtual)
        ]
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            for table in tables:
                conn.execute(f'DELETE FROM "{table}"')  # noqa: S608 - names from sqlite_master
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
