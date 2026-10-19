"""Pictures on this PC: stable-diffusion.cpp run once per picture, its progress read as it goes.

One picture at a time: two at once would both be slower and could run the GPU out of memory next
to the chat model. The engine never downloads anything unless you press the button.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from server.hardware import registry_files
from server.hardware.downloader import HF_FILE_URL, matches, stream_to
from server.imagegen import catalog, runtime
from server.models.images import ImageModelOption, ImageStatus
from server.settings import Settings

log = logging.getLogger("jarvis.images")
STEP = re.compile(r"(\d+)/(\d+)")


class ImageError(RuntimeError):
    pass


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

    def model_path(self, key: str) -> Path:
        entry = catalog.entry(key) or {}
        return self.models_dir / "images" / str(entry.get("file_glob", key))

    def status(self) -> ImageStatus:
        key = self.settings.images.model
        options = [
            ImageModelOption(
                key=m["key"],
                display_name=m["display_name"],
                why=m["why"],
                license=m["license"],
                installed=self.model_path(m["key"]).is_file(),
            )
            for m in catalog.IMAGE_MODELS
        ]
        have_model = self.model_path(key).is_file()
        have_runtime = self.binary() is not None
        return ImageStatus(
            runtime=have_runtime,
            model=key,
            model_installed=have_model,
            ready=have_runtime and have_model,
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
            self.settings.images.model = key
            self._task = asyncio.get_running_loop().create_task(self._install(key))
        return self.status()

    async def _install(self, key: str) -> None:
        self.state, self.detail = "installing", ""
        try:
            if self.binary() is None:
                await self._install_runtime()
            if not self.model_path(key).is_file():
                await self._install_model(key)
            self.state, self.detail = "idle", "Ready."
        except Exception as exc:  # noqa: BLE001 - the sheet shows it; downloading again resumes
            log.warning("image install failed: %s", exc)
            self.state, self.detail = "failed", str(exc)

    def _progress(self, label: str, total: int | None) -> Any:
        def report(done: int) -> None:
            self.detail = (
                f"{label}: {done / 1e6:.0f} of {(total or 0) / 1e6:.0f} MB" if total else label
            )

        return report

    async def _install_runtime(self) -> None:
        self.detail = "Finding stable-diffusion.cpp for this PC"
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            release = (await client.get(runtime.RELEASES)).json()
        asset = runtime.pick_asset(release.get("assets") or [])
        if asset is None:
            raise ImageError("No stable-diffusion.cpp build for this system in its latest release.")
        target = runtime.folder(self.models_dir)
        part = target.with_suffix(".zip.part")
        await stream_to(
            asset["browser_download_url"], part, self._progress(asset["name"], asset.get("size"))
        )
        expected = runtime.digest_of(asset)
        if expected and not await asyncio.to_thread(matches, part, expected):
            part.unlink(missing_ok=True)
            raise ImageError(f"{asset['name']} did not match its published sha256.")
        if await asyncio.to_thread(runtime.unpack, part, target) is None:
            raise ImageError("The stable-diffusion.cpp download had no sd program in it.")
        part.unlink(missing_ok=True)

    async def _install_model(self, key: str) -> None:
        entry = catalog.entry(key) or {}
        self.detail = f"Finding {entry['display_name']}"
        filename, size, sha256 = await asyncio.to_thread(registry_files.resolve_file, entry)
        if filename is None:
            raise ImageError(f"Could not reach {entry['hf_repo']} on Hugging Face.")
        final = self.model_path(key)
        part = final.with_suffix(".part")
        await stream_to(
            HF_FILE_URL.format(repo=entry["hf_repo"], filename=filename),
            part,
            self._progress(entry["display_name"], size),
        )
        if sha256 and not await asyncio.to_thread(matches, part, sha256):
            part.unlink(missing_ok=True)
            raise ImageError(
                f"{entry['display_name']} did not match its sha256, so it was discarded."
            )
        part.replace(final)

    # -- making a picture --------------------------------------------------------------------

    def command(self, prompt: str, negative: str, seed: int, out: Path) -> list[str]:
        key = self.settings.images.model
        entry = catalog.entry(key) or {}
        binary = self.binary()
        if binary is None or not self.model_path(key).is_file():
            raise ImageError("Making pictures is not set up yet: get it in Settings > Images.")
        argv = [
            str(binary),
            "-m", str(self.model_path(key)),
            "-p", prompt,
            "-o", str(out),
            "-W", str(entry.get("width", 512)),
            "-H", str(entry.get("height", 512)),
            "--steps", str(entry.get("steps", 4)),
            "--cfg-scale", str(entry.get("cfg", 1.0)),
            "--sampling-method", "euler_a",
            "-s", str(seed),
        ]  # fmt: skip
        if negative:
            argv += ["-n", negative]
        if self.settings.images.vae_tiling:
            argv.append("--vae-tiling")
        return argv + list(self.settings.images.extra_args)

    async def generate(self, prompt: str, negative: str = "", seed: int | None = None) -> bytes:
        async with self._lock:
            seed = seed if seed is not None else random.randint(0, 2**31 - 1)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "out.png"
                argv = self.command(prompt, negative, seed, out)
                self.state, self.step, self.total, self.detail = "generating", 0, 0, "Starting"
                started = time.monotonic()
                try:
                    await asyncio.wait_for(self._run(argv), timeout=self.settings.images.timeout_s)
                except TimeoutError as exc:
                    raise ImageError("The picture took too long and was stopped.") from exc
                finally:
                    self.state = "idle"
                if not out.is_file():
                    raise ImageError(f"stable-diffusion.cpp made no picture. {self.detail}".strip())
                self.detail = f"Made in {time.monotonic() - started:.1f}s"
                return out.read_bytes()

    async def _run(self, argv: list[str]) -> None:
        process = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
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
