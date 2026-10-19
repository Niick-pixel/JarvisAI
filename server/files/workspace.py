"""The folders you opened in Files, and every way their contents are read or changed.

Every path is resolved to its real location before it is checked against the folder, with the
same rules agents live by (server/tools/sandbox.py): no escaping with `..` or a symlink, and
credential files are refused even inside the folder. Every write is preceded by a backup, so the
last change to any file can be undone - whether you made it or Jarvis did.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from server.files import docs
from server.ids import new_id
from server.models.files import Entry, FileContent, Root, RunResult
from server.tools.sandbox import Denied, Sandbox

SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", "dist", "build", ".next", ".idea", ".vs", "target"}  # fmt: skip
MAX_ENTRIES = 500
BACKUPS_KEPT = 20
RUN_TIMEOUT_S = 300
MAX_OUTPUT = 20_000


class Workspace:
    def __init__(self, data_dir: Path) -> None:
        self._file = data_dir / "files.json"
        self._backups = data_dir / "files-backups"

    # -- folders ---------------------------------------------------------------------------------
    def roots(self) -> list[Root]:
        try:
            return [Root(**r) for r in json.loads(self._file.read_text())]
        except (OSError, ValueError, TypeError):
            return []

    def _save_roots(self, roots: list[Root]) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps([r.model_dump() for r in roots]))

    def add_root(self, raw: str) -> Root:
        path = Path(raw).expanduser().resolve()
        if not path.is_dir():
            raise Denied(f"{path} is not a folder.")
        existing = next((r for r in self.roots() if Path(r.path) == path), None)
        if existing:
            return existing
        root = Root(id=new_id("root"), path=str(path), name=path.name or str(path))
        self._save_roots([*self.roots(), root])
        return root

    def remove_root(self, root_id: str) -> None:
        self._save_roots([r for r in self.roots() if r.id != root_id])

    def root(self, root_id: str) -> Root:
        found = next((r for r in self.roots() if r.id == root_id), None)
        if found is None:
            raise Denied("That folder is no longer open in Files.")
        return found

    def resolve(self, root_id: str, rel: str) -> Path:
        base = Path(self.root(root_id).path)
        sandbox = Sandbox(read_roots=(base,), write_root=base)
        return sandbox.resolve_write(str(base / rel))

    # -- reading ---------------------------------------------------------------------------------
    def listing(self, root_id: str, rel: str = "") -> list[Entry]:
        folder = self.resolve(root_id, rel)
        base = Path(self.root(root_id).path)
        if not folder.is_dir():
            raise Denied(f"{rel or '.'} is not a folder.")
        entries = []
        for child in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.name in SKIP or (child.name.startswith(".") and child.name != ".github"):
                continue
            is_dir = child.is_dir()
            entries.append(
                Entry(
                    name=child.name,
                    path=child.relative_to(base).as_posix(),
                    dir=is_dir,
                    size=0 if is_dir else child.stat().st_size,
                )
            )
            if len(entries) >= MAX_ENTRIES:
                break
        return entries

    def read(self, root_id: str, rel: str) -> FileContent:
        path = self.resolve(root_id, rel)
        kind, text, data = docs.read(path)
        return FileContent(
            root=root_id,
            path=rel,
            kind=kind,
            text=text,
            version=docs.version(data),
            size=len(data),
            note=docs.DOCX_NOTE if kind == "docx" else "",
            can_undo=bool(self._backups_of(path)),
        )

    # -- writing ---------------------------------------------------------------------------------
    def write(self, root_id: str, rel: str, expected_version: str, new_text: str) -> FileContent:
        current = self.read(root_id, rel)
        if current.version != expected_version:
            raise Denied(f"{rel} changed on disk since it was opened. Open it again first.")
        path = self.resolve(root_id, rel)
        self._backup(path)
        docs.write(path, current.kind, current.text, new_text)
        return self.read(root_id, rel)

    def undo(self, root_id: str, rel: str) -> FileContent:
        path = self.resolve(root_id, rel)
        backups = self._backups_of(path)
        if not backups:
            raise Denied(f"There is nothing to undo for {rel}.")
        latest = backups[-1]
        path.write_bytes(latest.read_bytes())
        latest.unlink()
        return self.read(root_id, rel)

    def _folder_for(self, path: Path) -> Path:
        return self._backups / hashlib.sha256(str(path).encode()).hexdigest()[:16]

    def _backups_of(self, path: Path) -> list[Path]:
        folder = self._folder_for(path)
        return sorted(folder.glob("*.bak")) if folder.is_dir() else []

    def _backup(self, path: Path) -> None:
        folder = self._folder_for(path)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{time.time_ns()}.bak").write_bytes(path.read_bytes())
        for old in self._backups_of(path)[:-BACKUPS_KEPT]:
            old.unlink(missing_ok=True)

    # -- running ---------------------------------------------------------------------------------
    async def run(self, root_id: str, command: str) -> RunResult:
        """A command you typed and pressed Run on, in the folder. Nothing runs that you did not."""
        cwd = Path(self.root(root_id).path)
        started = time.perf_counter()
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            # CREATE_NO_WINDOW: the windowed app has no console, so a command must not open one.
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        timed_out = False
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=RUN_TIMEOUT_S)
        except TimeoutError:
            process.kill()
            output, timed_out = (await process.communicate())[0], True
        text = output.decode("utf-8", errors="replace")
        if len(text) > MAX_OUTPUT:
            text = f"… {len(text) - MAX_OUTPUT} characters cut …\n" + text[-MAX_OUTPUT:]
        return RunResult(
            command=command,
            exit_code=process.returncode if process.returncode is not None else -1,
            output=text,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            timed_out=timed_out,
        )
