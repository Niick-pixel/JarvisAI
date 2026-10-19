"""Fetching Kokoro: two files from its release, resumable, each checked against its pinned sha256
before it is renamed into place. Only when you press the button in Settings > Voice."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx

from server.hardware.downloader import matches, stream_to
from server.models.voice import VoicePackProgress
from server.settings import Settings
from server.voice import kokoro
from server.voice.pack import remote_size


class KokoroPack:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.progress = VoicePackProgress()
        self._task: asyncio.Task[None] | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> VoicePackProgress:
        if not self.busy:
            self.progress = VoicePackProgress(state="downloading", detail="Checking sizes")
            self._task = asyncio.get_running_loop().create_task(self._run())
        return self.progress

    def cancel(self) -> None:
        if self._task is not None and self.busy:
            self._task.cancel()

    async def _run(self) -> None:
        target_dir = kokoro.folder(self.settings)
        try:
            urls = {name: kokoro.RELEASE + name for name in kokoro.FILES}
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                sizes = {name: await remote_size(client, url) for name, url in urls.items()}
            self._update(bytes_total=sum(sizes.values()), detail="")
            base = 0
            for name, url in urls.items():
                target = target_dir / name
                if not target.is_file():
                    part = target.with_name(name + ".part")
                    self._update(file=name)
                    await stream_to(url, part, self._grew(base))
                    self._update(state="verifying")
                    if not await asyncio.to_thread(matches, part, kokoro.FILES[name]):
                        part.unlink(missing_ok=True)
                        raise ValueError(f"{name} did not match its published checksum")
                    part.replace(target)
                    self._update(state="downloading")
                base += sizes[name]
                self._update(bytes_done=base)
            # What you just fetched is what you meant to hear.
            kokoro.choose(self.settings, engine="kokoro")
            self._update(state="done", file="", detail="The natural voice is ready.")
        except asyncio.CancelledError:
            self._update(state="cancelled", detail="Paused. Getting it again resumes from here.")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            self._update(state="failed", detail=f"{exc}. Trying again resumes from here.")

    def _grew(self, start: int) -> Callable[[int], None]:
        return lambda done: self._update(bytes_done=start + done)

    def _update(self, **fields: object) -> None:
        self.progress = self.progress.model_copy(update=fields)
