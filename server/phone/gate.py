"""Who may come in from the network. Every request that did not come from this PC must show a
paired device's token (or the configured server auth_token) - and the few things that change the
PC itself stay on the PC.

Plain ASGI rather than an HTTP middleware so WebSockets pass through the same door.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from http.cookies import SimpleCookie
from typing import Any

from server.phone import pairing
from server.settings import is_loopback

Scope = dict[str, Any]
ASGIApp = Callable[[Scope, Any, Any], Awaitable[None]]

OPEN = ("/pair", "/api/phone/pair")
"""Reachable without a token: the pairing page and the call it makes."""
PC_ONLY = ("/api/phone", "/api/updates", "/api/files/run", "/api/hardware/download")
"""Never from a phone, paired or not: managing devices, installing updates, running commands."""


def _headers(scope: Scope) -> dict[str, str]:
    return {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}


def token_of(scope: Scope) -> str:
    headers = _headers(scope)
    bearer = headers.get("authorization", "")
    if bearer.lower().startswith("bearer "):
        return bearer[7:].strip()
    cookie = SimpleCookie(headers.get("cookie", ""))
    morsel = cookie.get(pairing.COOKIE)
    return morsel.value if morsel else ""


class Gate:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    def _gated(self, scope: Scope, state: Any) -> bool:
        server = scope.get("server") or ("", 0)
        client = (scope.get("client") or ("", 0))[0]
        if server[1] == state.settings.server.phone_port:
            return True
        return not is_loopback(state.settings.server.host) and not is_loopback(client)

    async def __call__(self, scope: Scope, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        state = scope["app"].state.app
        path: str = scope.get("path", "")
        if not self._gated(scope, state) or path in OPEN:
            return await self.app(scope, receive, send)
        token = token_of(scope)
        admin = bool(state.settings.server.auth_token) and token == state.settings.server.auth_token
        device = None
        if token and not admin:
            with state.db.session() as conn:
                device = pairing.device_for(conn, token)
        if not (admin or device):
            return await self._refuse(scope, send, 401, "Pair this device first.")
        if device and path.startswith(PC_ONLY):
            return await self._refuse(scope, send, 403, "That can only be done on the PC itself.")
        return await self.app(scope, receive, send)

    async def _refuse(self, scope: Scope, send: Any, status: int, message: str) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4000 + status})
            return
        if status == 401 and not scope.get("path", "").startswith("/api"):
            # A person, not a script: take them to the pairing page.
            await send(
                {"type": "http.response.start", "status": 303, "headers": [(b"location", b"/pair")]}
            )
            await send({"type": "http.response.body", "body": b""})
            return
        body = json.dumps({"code": "invalid_request", "message": message}).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})
