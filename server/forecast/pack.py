"""The Kronos weights, fetched from inside the app when you press the button - never otherwise.

Two small repos on Hugging Face: the model (Kronos-small, about 100MB) and the tokenizer that
turns candles into its tokens. Same rules as the voice pack: resumable `.part` files, the sha256
Hugging Face publishes checked before a file counts.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from server.forecast.engine import weights_dir
from server.hardware.downloader import HF_FILE_URL, matches, stream_to
from server.models.voice import VoicePackProgress
from server.settings import Settings
from server.voice.pack import remote_size

FILES = ("config.json", "model.safetensors")


def plan(settings: Settings) -> list[tuple[str, Path]]:
    cfg = settings.forecast
    return [
        (HF_FILE_URL.format(repo=repo, filename=name), weights_dir(settings, repo) / name)
        for repo in (cfg.tokenizer, cfg.model)
        for name in FILES
    ]


class ForecastPack:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.progress = VoicePackProgress()
        self._task: asyncio.Task[None] | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> VoicePackProgress:
        if not self.busy:
            self._task = asyncio.get_running_loop().create_task(self._run())
            self.progress = VoicePackProgress(state="downloading", detail="Checking sizes")
        return self.progress

    async def _run(self) -> None:
        try:
            files = plan(self.settings)
            async with httpx.AsyncClient(timeout=30.0) as client:
                sizes = [await remote_size(client, url) for url, _ in files]
            self._update(bytes_total=sum(sizes), detail="")
            base = 0
            for (url, target), size in zip(files, sizes, strict=True):
                if not target.is_file():
                    await self._fetch(url, target, base)
                base += size
                self._update(bytes_done=base)
            self._update(state="done", file="", detail="Forecasting is ready.")
        except asyncio.CancelledError:
            self._update(state="cancelled", detail="Paused. Getting it again resumes from here.")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            self._update(state="failed", detail=f"{exc}. Trying again resumes from here.")

    async def _fetch(self, url: str, target: Path, base: int) -> None:
        part = target.with_name(target.name + ".part")
        self._update(file=target.name)
        _, sha256 = await stream_to(url, part, lambda done: self._update(bytes_done=base + done))
        if sha256:
            self._update(state="verifying")
            if not await asyncio.to_thread(matches, part, sha256):
                part.unlink(missing_ok=True)
                raise ValueError(f"{target.name} did not match its published checksum")
            self._update(state="downloading")
        part.replace(target)

    def _update(self, **fields: object) -> None:
        self.progress = self.progress.model_copy(update=fields)
