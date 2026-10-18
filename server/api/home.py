"""Home Assistant: connect it, see your devices by room, control them, and send it commands."""

from __future__ import annotations

from fastapi import APIRouter

from server.chat import titles
from server.db import repo
from server.deps import State
from server.errors import SovereignError
from server.home.client import HomeError
from server.home.hub import Hub
from server.models.conversation import ConversationUpdate
from server.models.home import (
    AssistRequest,
    AssistResult,
    Device,
    HomeActionRequest,
    HomeConnection,
    HomePrefs,
    HomeStatus,
)

router = APIRouter(prefix="/api/home", tags=["home"])
ASSIST_MODEL = "home-assistant"
"""The model_id on a turn Home Assistant answered, so the chat can say who did."""


def _hub(state: State) -> Hub:
    assert state.home is not None
    return state.home


def _unavailable(exc: HomeError) -> SovereignError:
    return SovereignError("provider_unavailable", str(exc), status_code=502)


@router.get("/status")
async def status(state: State) -> HomeStatus:
    return await _hub(state).status()


@router.put("/connection")
async def connect(body: HomeConnection, state: State) -> HomeStatus:
    try:
        return await _hub(state).connect(body.url, body.token)
    except HomeError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc


@router.delete("/connection")
def disconnect(state: State) -> HomeStatus:
    _hub(state).disconnect()
    return HomeStatus(configured=False)


@router.put("/prefs")
async def prefs(body: HomePrefs, state: State) -> HomeStatus:
    _hub(state).set_route_chat(body.route_chat)
    return await _hub(state).status()


@router.get("/devices")
async def devices(state: State) -> list[Device]:
    try:
        return await _hub(state).devices()
    except HomeError as exc:
        raise _unavailable(exc) from exc


@router.post("/action")
async def act(body: HomeActionRequest, state: State) -> list[Device]:
    """Do one thing, then return every device, so the tile shows what really happened."""
    try:
        await _hub(state).act(body)
        return await _hub(state).devices()
    except ValueError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc
    except HomeError as exc:
        raise _unavailable(exc) from exc


@router.post("/assist")
async def assist(body: AssistRequest, state: State) -> AssistResult:
    """Offer a message to Home Assistant's own local sentence matcher. If it recognises a home
    command it carries it out, and the exchange is written into the chat like any other turn;
    if not, nothing is written and the message goes to the model as usual."""
    hub = _hub(state)
    if not hub.route_chat or not body.text.strip():
        return AssistResult(handled=False)
    try:
        handled, reply = await hub.client().assist(body.text.strip())
    except HomeError:
        return AssistResult(handled=False)  # Home Assistant being off must not block chatting
    if not handled:
        return AssistResult(handled=False)
    cid = body.conversation_id
    if cid:
        with state.db.session() as conn:
            conversation = repo.conversations.get(conn, cid)
            if conversation is not None:
                asked = repo.messages.create(
                    conn,
                    conversation_id=cid,
                    role="user",
                    content=body.text.strip(),
                    parent_id=conversation.active_leaf_id,
                )
                answered = repo.messages.create(
                    conn,
                    conversation_id=cid,
                    role="assistant",
                    content=reply or "Done.",
                    parent_id=asked.id,
                    model_id=ASSIST_MODEL,
                )
                repo.conversations.touch(conn, cid, answered.id)
                if titles.needs_title(conversation.title):
                    repo.conversations.update(
                        conn, cid, ConversationUpdate(title=titles.instant(body.text))
                    )
    return AssistResult(handled=True, reply=reply or "Done.", conversation_id=cid)
