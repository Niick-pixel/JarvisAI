"""The voice pack: the Whisper model that listens and the Piper voice that speaks, fetched from
inside the app when you press the button - and never otherwise.

Same rules as a model download (server/hardware/downloader.py): resumable `.part` files, the
sha256 Hugging Face publishes checked before a file counts, and a file only renamed into place
once it is whole. `make voice` fetches the same files into the same places.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from server.hardware.downloader import HF_FILE_URL, matches, stream_to
from server.models.voice import VoicePackProgress
from server.settings import Settings
from server.voice import capability

WHISPER_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base": "Systran/faster-whisper-base",
    "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small",
    "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium",
    "medium.en": "Systran/faster-whisper-medium.en",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
}
WHISPER_REQUIRED = ["model.bin", "config.json"]
WHISPER_OPTIONAL = ["tokenizer.json", "vocabulary.txt"]
"""Optional because they differ between sizes; a 404 on one of these is not a failure."""
PIPER_REPO = "rhasspy/piper-voices"


def piper_paths(name: str) -> tuple[str, str]:
    """`en_US-lessac-medium` lives at `en/en_US/lessac/medium/` in the voices repo."""
    try:
        locale, speaker, quality = name.split("-")
        language = locale.split("_")[0]
    except ValueError as exc:
        raise ValueError(f"Voice name {name!r} is not <locale>-<speaker>-<quality>.") from exc
    folder = f"{language}/{locale}/{speaker}/{quality}"
    return f"{folder}/{name}.onnx", f"{folder}/{name}.onnx.json"


def plan(settings: Settings) -> list[tuple[str, Path, bool]]:
    """(url, where it goes, required) for every file the pack is made of."""
    model_id = settings.voice.stt_model
    repo = WHISPER_REPOS.get(model_id)
    if repo is None:
        raise ValueError(f"No known download for Whisper {model_id!r}.")
    folder = capability.whisper_dir(settings, model_id)
    files = [
        (HF_FILE_URL.format(repo=repo, filename=name), folder / name, name in WHISPER_REQUIRED)
        for name in WHISPER_REQUIRED + WHISPER_OPTIONAL
    ]
    onnx, config = capability.voice_files(settings, settings.voice.tts_voice)
    for remote, local in zip(piper_paths(settings.voice.tts_voice), (onnx, config), strict=True):
        files.append((HF_FILE_URL.format(repo=PIPER_REPO, filename=remote), local, True))
    return files


async def _size(client: httpx.AsyncClient, url: str) -> int:
    response = await client.head(url, follow_redirects=False)
    if response.status_code == 404:
        return 0
    linked = response.headers.get("x-linked-size")
    if linked:
        return int(linked)
    if response.is_redirect:
        response = await client.head(url, follow_redirects=True)
    return int(response.headers.get("content-length", 0))


class VoicePack:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.progress = VoicePackProgress()
        self._task: asyncio.Task[None] | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> VoicePackProgress:
        if not self.busy:
            task = asyncio.get_running_loop().create_task(self._run())
            self.progress = VoicePackProgress(state="downloading", detail="Checking sizes")
            self._task = task
        return self.progress

    def cancel(self) -> None:
        if self._task is not None and self.busy:
            self._task.cancel()

    async def _run(self) -> None:
        try:
            files = plan(self.settings)
            async with httpx.AsyncClient(timeout=30.0) as client:
                sizes = [await _size(client, url) for url, _, _ in files]
            self._update(bytes_total=sum(sizes), detail="")
            base = 0
            for (url, target, required), size in zip(files, sizes, strict=True):
                if not target.is_file() and (size or required):
                    await self._fetch(url, target, base)
                base += size
                self._update(bytes_done=base)
            self._update(state="done", file="", detail="Voice is ready.")
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
