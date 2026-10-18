"""The one Home Assistant connection: saved settings, a cached status, and every way in.

The address and token live in `data/home.json` beside your database - entered in the Home sheet,
not config.toml, so connecting never means editing a file. The token gives control of your home:
it stays on this PC and is never sent anywhere but the Home Assistant you named.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from server.home import devices
from server.home.client import HomeAssistant, HomeError
from server.models.home import Device, HomeActionRequest, HomeStatus


class Hub:
    def __init__(self, data_dir: Path) -> None:
        self._file = data_dir / "home.json"
        self._saved: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            saved: dict[str, Any] = json.loads(self._file.read_text())
            return saved
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._saved))

    @property
    def route_chat(self) -> bool:
        return bool(self._saved.get("route_chat", True))

    def client(self) -> HomeAssistant:
        if not self._saved.get("url"):
            raise HomeError("Home Assistant is not connected. Connect it in Home.")
        return HomeAssistant(self._saved["url"], self._saved.get("token", ""))

    async def status(self) -> HomeStatus:
        if not self._saved.get("url"):
            return HomeStatus(configured=False)
        base = HomeStatus(configured=True, url=self._saved["url"], route_chat=self.route_chat)
        try:
            config = await self.client().config()
        except HomeError as exc:
            return base.model_copy(update={"error": str(exc)})
        return base.model_copy(
            update={
                "connected": True,
                "name": str(config.get("location_name", "")),
                "version": str(config.get("version", "")),
            }
        )

    async def connect(self, url: str, token: str) -> HomeStatus:
        """Checked before it is saved: a typo should fail here, not on the first command."""
        url = url.strip().rstrip("/")
        if "://" not in url:
            url = f"http://{url}"  # what people type: homeassistant.local:8123
        if not url.startswith(("http://", "https://")):
            raise HomeError("The address starts with http:// or https://.")
        await HomeAssistant(url, token.strip()).config()
        self._saved.update({"url": url, "token": token.strip()})
        self._save()
        return await self.status()

    def disconnect(self) -> None:
        self._saved = {}
        self._save()

    def set_route_chat(self, on: bool) -> None:
        self._saved["route_chat"] = on
        self._save()

    async def devices(self) -> list[Device]:
        client = self.client()
        return devices.devices(await client.states(), await client.areas())

    async def act(self, request: HomeActionRequest) -> None:
        domain, service, data = devices.service(request)
        await self.client().call(domain, service, data)
