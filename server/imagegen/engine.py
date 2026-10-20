"""Pictures on this PC: stable-diffusion.cpp run once per picture, its progress read as it goes.

One picture at a time: two at once would both be slower and could run the GPU out of memory next
to the chat model. The engine never downloads anything unless you press the button.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from server.imagegen import catalog, downloads, parts, runtime
from server.imagegen.downloads import ImageError
from server.models.images import ImageModelOption, ImageStatus
from server.settings import Settings

log = logging.getLogger("jarvis.images")
STEP = re.compile(r"(\d+)/(\d+)")


class ImageEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = "idle"
        self.detail = ""
        self.step = self.total = 0
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    @property
    def models_dir(self) -> Path:
        return self.settings.paths.models_dir

    def binary(self) -> Path | None:
        if self.settings.images.binary:
            custom = Path(self.settings.images.binary)
            return custom if custom.is_file() else None
        return runtime.find_binary(runtime.folder(self.models_dir))

    def installed(self, key: str) -> bool:
        found = catalog.entry(key)
        return found is not None and parts.installed(self.models_dir, found)

    def status(self) -> ImageStatus:
        key = self.settings.images.model
        video = catalog.video_key()
        options = [
            ImageModelOption(
                key=m["key"],
                display_name=m["display_name"],
                why=m["why"],
                license=m["license"],
                installed=self.installed(m["key"]),
                video=bool(m.get("video")),
                heavy=bool(m.get("heavy")),
                size_gb=float(m.get("size_gb", 0)),
            )
            for m in catalog.IMAGE_MODELS
        ]
        have_model = self.installed(key)
        have_runtime = self.binary() is not None
        return ImageStatus(
            runtime=have_runtime,
            model=key,
            model_installed=have_model,
            ready=have_runtime and have_model,
            video_ready=have_runtime and video is not None and self.installed(video),
            options=options,
            state=self.state,  # type: ignore[arg-type]
            detail=self.detail,
            step=self.step,
            total=self.total,
        )

    # -- installing ------------------------------------------------------------------------

    def install(self, key: str) -> ImageStatus:
        if catalog.entry(key) is None:
            raise ImageError(f"No image model called {key!r}.")
        if self._task is None or self._task.done():
            if not (catalog.entry(key) or {}).get("video"):
                self.settings.images.model = key
            self._task = asyncio.get_running_loop().create_task(self._install(key))
        return self.status()

    async def _install(self, key: str) -> None:
        self.state, self.detail = "installing", ""
        try:
            if self.binary() is None:
                await self._install_runtime()
            for spec in parts.files(catalog.entry(key) or {}):
                if not parts.path(self.models_dir, spec).is_file():
                    await self._install_file(key, spec)
            self.state, self.detail = "idle", "Ready."
        except Exception as exc:  # noqa: BLE001 - the sheet shows it; downloading again resumes
            log.warning("image install failed: %s", exc)
            self.state, self.detail = "failed", str(exc)

    def _progress(self, label: str, total: int | None) -> Callable[[int], None]:
        def report(done: int) -> None:
            self.detail = (
                f"{label}: {done / 1e6:.0f} of {(total or 0) / 1e6:.0f} MB" if total else label
            )

        return report

    async def _install_runtime(self) -> None:
        await downloads.runtime_build(self.models_dir, self._say, self._progress)

    async def _install_file(self, key: str, spec: dict[str, Any]) -> None:
        label = f"{(catalog.entry(key) or {})['display_name']} ({spec['save_as']})"
        await downloads.part(self.models_dir, spec, label, self._say, self._progress)

    def _say(self, detail: str) -> None:
        self.detail = detail

    # -- making a picture --------------------------------------------------------------------

    def command(
        self, prompt: str, negative: str, seed: int, out: Path, key: str | None = None
    ) -> list[str]:
        key = key or self.settings.images.model
        entry = catalog.entry(key) or {}
        binary = self.binary()
        if binary is None or not self.installed(key):
            what = "Making videos" if entry.get("video") else "Making pictures"
            raise ImageError(f"{what} is not set up yet: get it in Images.")
        video = ["-M", "vid_gen", "--video-frames", str(entry.get("frames", 33))]
        argv = [
            str(binary),
            *(video if entry.get("video") else []),
            *parts.model_flags(self.models_dir, entry),
            "-p", prompt,
            "-o", str(out),
            "-W", str(entry.get("width", 512)),
            "-H", str(entry.get("height", 512)),
            "--steps", str(entry.get("steps", 4)),
            "--cfg-scale", str(entry.get("cfg", 1.0)),
            "--sampling-method", str(entry.get("sampler", "euler_a")),
            "-s", str(seed),
        ]  # fmt: skip
        negative = negative or str(entry.get("negative", ""))
        if negative:
            argv += ["-n", negative]
        argv += list(entry.get("args", []))
        if self.settings.images.vae_tiling:
            argv.append("--vae-tiling")
        return argv + list(self.settings.images.extra_args)

    async def generate(
        self, prompt: str, negative: str = "", seed: int | None = None, video: bool = False
    ) -> bytes:
        """A PNG - or, for video, a WebM (animated WebP from a build without WebM)."""
        key = catalog.video_key() if video else None
        async with self._lock:
            seed = seed if seed is not None else random.randint(0, 2**31 - 1)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / ("out.webm" if video else "out.png")
                argv = self.command(prompt, negative, seed, out, key)
                self.state, self.step, self.total, self.detail = "generating", 0, 0, "Starting"
                started = time.monotonic()
                try:
                    # A clip is dozens of frames: it gets far longer than a picture.
                    limit = self.settings.images.timeout_s * (4 if video else 1)
                    await asyncio.wait_for(self._run(argv), timeout=limit)
                except TimeoutError as exc:
                    raise ImageError("The picture took too long and was stopped.") from exc
                finally:
                    self.state = "idle"
                if video and not out.is_file():
                    # A build without WebM writes nothing for .webm; animated WebP plays too.
                    fallback = out.with_suffix(".webp")
                    self.state = "generating"
                    try:
                        await asyncio.wait_for(
                            self._run(self.command(prompt, negative, seed, fallback, key)),
                            timeout=self.settings.images.timeout_s * 4,
                        )
                    finally:
                        self.state = "idle"
                    out = fallback
                if not out.is_file():
                    raise ImageError(f"stable-diffusion.cpp made nothing. {self.detail}".strip())
                self.detail = f"Made in {time.monotonic() - started:.1f}s"
                return out.read_bytes()

    async def _run(self, argv: list[str]) -> None:
        # No console window on Windows: without the flag every picture flashed a black terminal.
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            creationflags=flags,
        )
        assert process.stdout is not None
        last = ""
        try:
            while chunk := await process.stdout.read(512):
                text = chunk.decode(errors="replace")
                for match in STEP.finditer(text):
                    self.step, self.total = int(match.group(1)), int(match.group(2))
                if text.strip():
                    last = text.strip().splitlines()[-1][:200]
            await process.wait()
        finally:
            if process.returncode is None:
                process.kill()
        if process.returncode != 0:
            self.detail = last
            raise ImageError(f"stable-diffusion.cpp stopped with code {process.returncode}: {last}")
