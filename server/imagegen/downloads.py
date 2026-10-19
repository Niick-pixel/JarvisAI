"""Fetching what pictures need: stable-diffusion.cpp itself, and each file of a model.

Both resumable through `.part` files, both checked against a published sha256 before they count -
GitHub's for the program, Hugging Face's for the weights.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from server.hardware import registry_files
from server.hardware.downloader import HF_FILE_URL, matches, stream_to
from server.imagegen import parts, runtime

Say = Callable[[str], None]
Progress = Callable[[str, int | None], Callable[[int], None]]


class ImageError(RuntimeError):
    pass


async def runtime_build(models_dir: Path, say: Say, progress: Progress) -> None:
    say("Finding stable-diffusion.cpp for this PC")
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        release = (await client.get(runtime.RELEASES)).json()
    asset = runtime.pick_asset(release.get("assets") or [])
    if asset is None:
        raise ImageError("No stable-diffusion.cpp build for this system in its latest release.")
    target = runtime.folder(models_dir)
    part = target.with_suffix(".zip.part")
    await stream_to(asset["browser_download_url"], part, progress(asset["name"], asset.get("size")))
    expected = runtime.digest_of(asset)
    if expected and not await asyncio.to_thread(matches, part, expected):
        part.unlink(missing_ok=True)
        raise ImageError(f"{asset['name']} did not match its published sha256.")
    if await asyncio.to_thread(runtime.unpack, part, target) is None:
        raise ImageError("The stable-diffusion.cpp download had no sd program in it.")
    part.unlink(missing_ok=True)


async def part(
    models_dir: Path, spec: dict[str, Any], label: str, say: Say, progress: Progress
) -> None:
    say(f"Finding {label}")
    filename, size, sha256 = await asyncio.to_thread(registry_files.resolve_file, spec)
    if filename is None:
        raise ImageError(f"Could not reach {spec['hf_repo']} on Hugging Face.")
    final = parts.path(models_dir, spec)
    final.parent.mkdir(parents=True, exist_ok=True)
    partial = final.with_name(final.name + ".part")
    await stream_to(
        HF_FILE_URL.format(repo=spec["hf_repo"], filename=filename), partial, progress(label, size)
    )
    if sha256 and not await asyncio.to_thread(matches, partial, sha256):
        partial.unlink(missing_ok=True)
        raise ImageError(f"{label} did not match its sha256, so it was discarded.")
    partial.replace(final)
