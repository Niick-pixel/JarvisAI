"""The wake word: "Hey Jarvis" starts voice mode, heard on this PC.

The browser streams 16 kHz microphone audio over a loopback WebSocket while the wake word is on;
the detector (server/voice/wake.py) scores every 80 ms and says "wake" once when "Hey Jarvis"
crosses the threshold. Audio is never written anywhere and never leaves the machine - and the
three small model files are fetched only when you turn the wake word on.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from server.deps import State
from server.errors import SovereignError
from server.hardware.downloader import matches, stream_to
from server.settings import Settings
from server.voice import wake

router = APIRouter(prefix="/api/voice/wake", tags=["voice"])
log = logging.getLogger("jarvis.wake")
THRESHOLD = 0.5
REFRACTORY_S = 2.5
"""After a wake, ignore the tail of the same "Hey Jarvis" rather than waking twice."""


class WakeStatus(BaseModel):
    installed: bool
    phrase: str = "Hey Jarvis"
    threshold: float = THRESHOLD


def folder(settings: Settings) -> Path:
    return settings.paths.models_dir / "wake"


@router.get("")
def status(state: State) -> WakeStatus:
    return WakeStatus(installed=wake.installed(folder(state.settings)))


@router.post("/install")
async def install(state: State) -> WakeStatus:
    """Fetch the three model files (about 3.5 MB), each checked against its pinned sha256."""
    target = folder(state.settings)
    for name, digest in wake.FILES.items():
        final = target / name
        if final.is_file() and matches(final, digest):
            continue
        part = final.with_suffix(".part")
        try:
            await stream_to(wake.RELEASE + name, part, lambda _: None)
        except Exception as exc:  # noqa: BLE001 - say what failed, in words
            raise SovereignError(
                "provider_unavailable", f"Could not download {name}: {exc}"
            ) from exc
        if not matches(part, digest):
            part.unlink(missing_ok=True)
            raise SovereignError(
                "invalid_request", f"{name} did not match its checksum; try again."
            )
        part.replace(final)
    return status(state)


@router.websocket("/listen")
async def listen(socket: WebSocket) -> None:
    state = socket.app.state.app
    await socket.accept()
    target = folder(state.settings)
    if not wake.installed(target):
        await socket.close(code=4404, reason="The wake word is not installed.")
        return
    detector = await asyncio.to_thread(wake.Detector, target)
    last_wake = 0.0
    try:
        while True:
            audio = np.frombuffer(await socket.receive_bytes(), dtype=np.int16)
            scores = await asyncio.to_thread(detector.feed, audio)
            best = max(scores, default=0.0)
            now = time.monotonic()
            if best >= THRESHOLD and now - last_wake > REFRACTORY_S:
                last_wake = now
                await socket.send_json({"wake": True, "score": round(best, 3)})
    except WebSocketDisconnect:
        return
