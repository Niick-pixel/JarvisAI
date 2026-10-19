"""The phone companion: turn it on, pair a phone with a code, see and revoke paired phones."""

from __future__ import annotations

import segno
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from server.db import repo
from server.deps import AppState, State
from server.errors import SovereignError
from server.models.phone import PairRequest, PhoneStatus, PhoneToggle
from server.phone import pairing
from server.phone.listener import addresses
from server.phone.page import PAIR_PAGE

router = APIRouter(tags=["phone"])
ENABLED = "phone_enabled"
YEAR_S = 365 * 24 * 3600


def snapshot(state: AppState) -> PhoneStatus:
    assert state.phone is not None and state.pairing is not None
    port = state.settings.server.phone_port
    urls = addresses(port)
    code = state.pairing.current() if state.phone.running else None
    qr = ""
    if code and urls:
        qr = segno.make(f"{urls[0]}/pair?code={code.value}", error="m").svg_inline(
            scale=5, dark="#16181D"
        )
    with state.db.session() as conn:
        devices = pairing.devices(conn)
    return PhoneStatus(
        enabled=state.phone.running,
        port=port,
        addresses=urls,
        code=code.value if code else "",
        code_expires_at=int(code.expires_at * 1000) if code else None,
        qr_svg=qr,
        devices=devices,
    )


async def switch(state: AppState, app: object, on: bool) -> str:
    assert state.phone is not None and state.pairing is not None
    if not on:
        await state.phone.stop()
        return ""
    error = await state.phone.start(app, state.settings.server.phone_port)
    if not error:
        state.pairing.new_code()
    return error


@router.get("/api/phone")
def status(state: State) -> PhoneStatus:
    return snapshot(state)


@router.post("/api/phone")
async def toggle(body: PhoneToggle, request: Request, state: State) -> PhoneStatus:
    error = await switch(state, request.app, body.enabled)
    with state.db.session() as conn:
        repo.settings.put(conn, ENABLED, body.enabled and not error)
    return snapshot(state).model_copy(update={"error": error})


@router.post("/api/phone/code")
def new_code(state: State) -> PhoneStatus:
    assert state.pairing is not None
    state.pairing.new_code()
    return snapshot(state)


@router.delete("/api/phone/devices/{device_id}")
def revoke(device_id: str, state: State) -> PhoneStatus:
    with state.db.session() as conn:
        pairing.revoke(conn, device_id)
    return snapshot(state)


@router.post("/api/phone/pair")
def pair(body: PairRequest, response: Response, state: State) -> dict[str, bool]:
    """The phone trades the code for its own token, kept in a cookie only this site can read."""
    assert state.pairing is not None
    with state.db.session() as conn:
        token = state.pairing.redeem(conn, body.code, body.name)
    if token is None:
        raise SovereignError(
            "invalid_request",
            "That code is wrong or has expired. Check the code on the PC, or make a new one there.",
            status_code=401,
        )
    response.set_cookie(
        pairing.COOKIE, token, max_age=YEAR_S, httponly=True, samesite="strict", path="/"
    )
    return {"paired": True}


@router.get("/pair", include_in_schema=False)
def pair_page() -> HTMLResponse:
    return HTMLResponse(PAIR_PAGE)
