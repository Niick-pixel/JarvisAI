"""Downloading one model, with progress you can watch, resume after a dropped connection, and a
hash check before the file is allowed to count as installed.

huggingface_hub's own downloader has no progress callback a web UI can read, so this streams the
file itself: to `<name>.part`, resuming from whatever an interrupted attempt left there, hashing
as it goes, and renaming only once the sha256 matches the registry. A half-downloaded model can
therefore never be mistaken for a model.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from server.db.connection import Database
from server.hardware import registry_files
from server.models.hardware import DownloadProgress

CHUNK = 1 << 20
HF_FILE_URL = "https://huggingface.co/{repo}/resolve/main/{filename}"


class Downloader:
    def __init__(self, db: Database, models_dir: Path) -> None:
        self.db = db
        self.models_dir = models_dir
        self.progress = DownloadProgress()
        self._task: asyncio.Task[None] | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(
        self,
        entry: dict[str, Any],
        ctx_len: int,
        on_done: Callable[[], Awaitable[object]] | None = None,
    ) -> DownloadProgress:
        self.progress = DownloadProgress(
            state="resolving", key=entry["key"], display_name=entry["display_name"]
        )
        self._task = asyncio.get_running_loop().create_task(self._run(entry, ctx_len, on_done))
        return self.progress

    def cancel(self) -> None:
        if self.busy and self._task is not None:
            self._task.cancel()

    async def _run(
        self,
        entry: dict[str, Any],
        ctx_len: int,
        on_done: Callable[[], Awaitable[object]] | None,
    ) -> None:
        try:
            filename, size, sha256 = await asyncio.to_thread(registry_files.resolve_file, entry)
            if filename is None:
                self._fail(f"could not reach the model registry for {entry['hf_repo']}")
                return
            self._update(filename=filename, bytes_total=size, state="downloading")
            target = self.models_dir / Path(filename).name
            await self._stream(HF_FILE_URL.format(repo=entry["hf_repo"], filename=filename), target)
            self._update(state="verifying")
            if sha256 and not await asyncio.to_thread(matches, target.with_suffix(".part"), sha256):
                target.with_suffix(".part").unlink(missing_ok=True)
                self._fail("the file's sha256 did not match the registry, so it was discarded")
                return
            target.with_suffix(".part").replace(target)
            with self.db.session() as conn:
                registry_files.register(conn, target, entry, sha256, ctx_len)
            self._update(state="done", path=str(target), detail=f"saved to {target}")
            if on_done is not None:
                await on_done()
        except asyncio.CancelledError:
            # The .part file is kept on purpose: pressing download again resumes from it.
            self._update(state="cancelled", detail="stopped; downloading again resumes from here")
        except (httpx.HTTPError, OSError) as exc:
            self._fail(f"{type(exc).__name__}: {exc}. Downloading again resumes from here.")

    async def _stream(self, url: str, target: Path) -> None:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        resumed, _ = await stream_to(
            url, target.with_suffix(".part"), lambda done: self._update(bytes_done=done)
        )
        self._update(resumed_from=resumed)

    def _update(self, **fields: Any) -> None:
        self.progress = self.progress.model_copy(update=fields)

    def _fail(self, detail: str) -> None:
        self._update(state="failed", detail=detail)


async def stream_to(url: str, part: Path, on_bytes: Callable[[int], None]) -> tuple[int, str]:
    """Fetch `url` into `part`, resuming from whatever an earlier attempt left there.

    Reports the bytes on disk as they grow. Returns how many bytes were already there, and the
    sha256 Hugging Face publishes for the file (its X-Linked-Etag), or "" when there is none.
    """
    part.parent.mkdir(parents=True, exist_ok=True)
    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    timeout = httpx.Timeout(30.0, read=120.0)
    async with (
        httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client,
        client.stream("GET", url, headers=headers) as response,
    ):
        etag = _linked_sha256(response.history, response.headers)
        if response.status_code == 416:  # already complete
            on_bytes(have)
            return have, etag
        response.raise_for_status()
        if have and response.status_code != 206:
            have = 0  # the server ignored the range: start over rather than corrupt the file
        done = have
        on_bytes(done)
        with part.open("ab" if have else "wb") as handle:
            async for chunk in response.aiter_bytes(CHUNK):
                await asyncio.to_thread(handle.write, chunk)
                done += len(chunk)
                on_bytes(done)
    return have, etag


def _linked_sha256(history: list[httpx.Response], headers: httpx.Headers) -> str:
    """Hugging Face names a large file's sha256 on the redirect that points at its storage."""
    for response in [*history, None]:
        source = response.headers if response is not None else headers
        value = source.get("x-linked-etag", "").strip('"')
        if len(value) == 64:
            return value
    return ""


def matches(path: Path, expected: str) -> bool:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest() == expected.lower()
