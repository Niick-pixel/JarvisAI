"""Finding, fetching and verifying a new version.

A release publishes `latest.json` beside its installer (see .github/workflows/windows-app.yml):

    {"version": "0.2.0", "notes": "...",
     "installer": {"url": "https://github.com/.../JarvisSetup.exe", "sha256": "...", "size": 1}}

Checking is one GET of that public file - no identifier, no counter, nothing about you. The
installer is fetched with the same resumable downloader models use, and it only counts once its
sha256 matches the one the release published. A half-fetched or tampered installer is deleted,
never run.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from server.hardware.downloader import matches, stream_to
from server.models.updates import UpdateStatus
from server.settings import Settings
from server.updates import install
from server.version import VERSION

FIRST_CHECK_DELAY_S = 30.0
"""Starting the model matters more than checking for updates; give it the first half minute."""


class Installer(BaseModel):
    url: str
    sha256: str
    size: int = 0


class Release(BaseModel):
    version: str
    notes: str = ""
    installer: Installer


def parse_version(text: str) -> tuple[int, ...]:
    """`v0.10.2` -> (0, 10, 2). Anything after the numbers (`-rc1`) is ignored, not compared."""
    numbers = re.match(r"v?(\d+(?:\.\d+)*)", text.strip())
    return tuple(int(n) for n in numbers.group(1).split(".")) if numbers else (0,)


def newer(candidate: str, current: str = VERSION) -> bool:
    return parse_version(candidate) > parse_version(current)


class Updater:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.folder = settings.paths.data_dir / "updates"
        self._prefs = self.folder / "prefs.json"
        self.status = UpdateStatus(
            current=VERSION, auto=self._load_auto(), can_install=install.supported()
        )
        self._release: Release | None = None
        self._task: asyncio.Task[None] | None = None

    # -- preferences ---------------------------------------------------------------------------
    def _load_auto(self) -> bool:
        try:
            return bool(json.loads(self._prefs.read_text()).get("auto", True))
        except (OSError, ValueError):
            return True

    def set_auto(self, auto: bool) -> UpdateStatus:
        self.folder.mkdir(parents=True, exist_ok=True)
        self._prefs.write_text(json.dumps({"auto": auto}))
        self._update(auto=auto)
        return self.status

    # -- the background loop -------------------------------------------------------------------
    async def run_forever(self) -> None:
        """Only the installed app checks by itself. A checkout never calls out unasked."""
        if not install.supported():
            return
        await asyncio.sleep(FIRST_CHECK_DELAY_S)
        while True:
            if self.status.auto and self.status.state not in ("ready", "installing"):
                await self.check(fetch=True)
            await asyncio.sleep(self.settings.updates.check_interval_hours * 3600)

    # -- check, fetch, install -----------------------------------------------------------------
    async def check(self, fetch: bool = False) -> UpdateStatus:
        if self.status.state in ("downloading", "installing"):
            return self.status
        self._update(state="checking", detail="")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
                response = await client.get(self.settings.updates.feed_url)
                response.raise_for_status()
            release = Release.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            logging.info("update check failed: %s", exc)
            self._update(state="failed", detail=f"Couldn't reach the update server ({exc}).")
            return self.status
        now = datetime.now(UTC).isoformat(timespec="seconds")
        self._update(checked_at=now, latest=release.version, notes=release.notes)
        if not newer(release.version):
            self._update(state="up_to_date", detail="")
            return self.status
        self._release = release
        if self._target(release).is_file():
            self._update(state="ready", detail="")
        else:
            self._update(state="available", bytes_total=release.installer.size)
            if fetch and install.supported():
                self.download()
        return self.status

    def download(self) -> UpdateStatus:
        if self._release is None or self.status.state not in ("available", "failed"):
            return self.status
        self._task = asyncio.get_running_loop().create_task(self._download(self._release))
        self._update(state="downloading", detail="")
        return self.status

    async def _download(self, release: Release) -> None:
        target = self._target(release)
        part = target.with_name(target.name + ".part")
        try:
            await stream_to(release.installer.url, part, lambda n: self._update(bytes_done=n))
            if not await asyncio.to_thread(matches, part, release.installer.sha256):
                part.unlink(missing_ok=True)
                raise ValueError(
                    "the download did not match the release's checksum, so it was deleted"
                )
            part.replace(target)
            self._prune(keep=target)
            self._update(state="ready", detail="")
        except asyncio.CancelledError:
            self._update(state="available", detail="Paused.")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            self._update(state="failed", detail=f"{exc}. Trying again resumes from here.")

    def install(self) -> UpdateStatus:
        if self._release is None or self.status.state != "ready" or not install.supported():
            return self.status
        self._update(state="installing", detail="Jarvis will close and reopen in a moment.")
        install.launch(self._target(self._release))
        return self.status

    # -- helpers -------------------------------------------------------------------------------
    def _target(self, release: Release) -> Path:
        safe = re.sub(r"[^0-9A-Za-z.]", "", release.version)
        return self.folder / f"JarvisSetup-{safe}.exe"

    def _prune(self, keep: Path) -> None:
        """One installer on disk at a time: each is most of a gigabyte."""
        for old in self.folder.glob("JarvisSetup-*.exe*"):
            if old != keep:
                old.unlink(missing_ok=True)

    def _update(self, **fields: object) -> None:
        self.status = self.status.model_copy(update=fields)
