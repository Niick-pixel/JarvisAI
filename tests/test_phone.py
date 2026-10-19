"""The phone companion: nothing from the network gets in without pairing, a code works once, a
revoked phone is out, and the things that change the PC stay on the PC."""

from __future__ import annotations

import asyncio
import socket

import httpx
from fastapi.testclient import TestClient

from server.main import create_app
from server.phone import pairing
from server.settings import Settings


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def phone(app: object, port: int) -> TestClient:
    """A client arriving on the phone listener's port, i.e. from the network."""
    return TestClient(app, base_url=f"http://testserver:{port}")  # type: ignore[arg-type]


def test_a_phone_must_pair_and_a_code_works_once(settings: Settings) -> None:
    app = create_app(settings)
    port = settings.server.phone_port
    with TestClient(app) as pc:
        net = phone(app, port)
        # Unpaired: a person is sent to the pairing page, a script gets 401.
        assert net.get("/", follow_redirects=False).headers["location"] == "/pair"
        assert net.get("/api/health").status_code == 401
        assert "Pair with Jarvis" in net.get("/pair").text

        code = app.state.app.pairing.new_code().value
        assert (
            net.post(
                "/api/phone/pair", json={"code": "000000" if code != "000000" else "111111"}
            ).status_code
            == 401
        )
        paired = net.post("/api/phone/pair", json={"code": code, "name": "Pixel"})
        assert paired.status_code == 200 and pairing.COOKIE in paired.cookies
        assert net.get("/api/health").status_code == 200  # the cookie is the key now
        again = phone(app, port).post("/api/phone/pair", json={"code": code})
        assert again.status_code == 401  # one code, one phone

        # The PC sees the phone and can take it back.
        [device] = pc.get("/api/phone").json()["devices"]
        assert device["name"] == "Pixel" and device["last_seen"]
        # Managing phones, updates and shell commands stay on the PC.
        assert net.get("/api/phone").status_code == 403
        assert net.post("/api/files/run", json={}).status_code == 403
        pc.delete(f"/api/phone/devices/{device['id']}")
        assert net.get("/api/health").status_code == 401


def test_a_code_gives_five_tries(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app):
        code = app.state.app.pairing.new_code().value
        wrong = "000000" if code != "000000" else "111111"
        net = phone(app, settings.server.phone_port)
        for _ in range(5):
            net.post("/api/phone/pair", json={"code": wrong})
        assert net.post("/api/phone/pair", json={"code": code}).status_code == 401


def test_the_configured_auth_token_also_opens_the_door(settings: Settings) -> None:
    settings.server.auth_token = "s3cret"
    app = create_app(settings)
    with TestClient(app):
        net = phone(app, settings.server.phone_port)
        assert net.get("/api/health").status_code == 401
        ok = net.get("/api/health", headers={"Authorization": "Bearer s3cret"})
        assert ok.status_code == 200


def test_the_listener_opens_and_closes_for_real(settings: Settings) -> None:
    settings.server.phone_port = free_port()
    app = create_app(settings)
    with TestClient(app) as pc:
        assert pc.post("/api/phone", json={"enabled": True}).json()["enabled"] is True
        status = pc.get("/api/phone").json()
        assert len(status["code"]) == 6

        async def knock() -> int:
            async with httpx.AsyncClient() as client:
                url = f"http://127.0.0.1:{settings.server.phone_port}/api/health"
                return (await client.get(url)).status_code

        assert pc.portal.call(knock) == 401  # the real door, refusing an unpaired caller
        assert pc.post("/api/phone", json={"enabled": False}).json()["enabled"] is False

        async def closed() -> bool:
            try:
                await asyncio.wait_for(knock(), timeout=2)
            except (httpx.ConnectError, TimeoutError):
                return True
            return False

        assert pc.portal.call(closed)
