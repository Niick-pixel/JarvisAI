"""The phone companion's door: a second listener on this PC's network address, open only while
the companion is on. It serves the same app in the same process (so a reply streams the same way)
behind the gate in gate.py, which turns away anything without a paired device's token.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
from collections.abc import Generator
from typing import Any

import psutil
import uvicorn

log = logging.getLogger("jarvis.phone")


class _Quiet(uvicorn.Server):
    """The main server owns Ctrl+C; this one must not take the signal handlers from it."""

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None, None, None]:
        yield


def addresses(port: int) -> list[str]:
    """Where a phone on the same network (or the same Tailscale) can reach this PC."""
    found: list[str] = []
    for entries in psutil.net_if_addrs().values():
        for entry in entries:
            if entry.family.name != "AF_INET":
                continue
            ip = ipaddress.ip_address(entry.address)
            if ip.is_loopback or ip.is_link_local:
                continue
            if ip.is_private or ip in ipaddress.ip_network("100.64.0.0/10"):
                found.append(f"http://{entry.address}:{port}")
    return sorted(set(found))


class PhoneListener:
    def __init__(self) -> None:
        self.server: _Quiet | None = None
        self.task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    async def start(self, app: Any, port: int) -> str:
        """Open the door. Returns "" when listening, else what went wrong (port taken...)."""
        if self.running:
            return ""
        config = uvicorn.Config(app, host="0.0.0.0", port=port, lifespan="off", log_level="warning")
        self.server = _Quiet(config)
        self.task = asyncio.get_running_loop().create_task(self.server.serve())
        for _ in range(50):
            if self.server.started:
                log.info("phone companion listening on port %d", port)
                return ""
            if self.task.done():
                break
            await asyncio.sleep(0.1)
        await self.stop()
        return f"Could not listen on port {port} - another program may be using it."

    async def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        if self.task is not None:
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await asyncio.wait_for(self.task, timeout=5)
        self.server = self.task = None
