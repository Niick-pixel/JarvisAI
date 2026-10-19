"""Agent mode in chat: start a turn that may use tools, and follow it while it works."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from server.chat.agentic import DEFAULT_TOOLS
from server.db import repo
from server.deps import State
from server.errors import NotFound
from server.models.params import SamplingParams
from server.models.tools import PendingCall

router = APIRouter(prefix="/api/chat/agent", tags=["chat"])


class AgentTurnRequest(BaseModel):
    conversation_id: str
    content: str
    tools: list[str] | None = None
    """None means every tool chat may use (DEFAULT_TOOLS)."""
    model_id: str | None = None
    params: SamplingParams = SamplingParams()


class AgentTurnStarted(BaseModel):
    run_id: str


class AgentTurn(BaseModel):
    run_id: str
    status: str
    live_run_id: str = ""
    """The generation streaming now - attach to it like any chat run."""
    calls: list[PendingCall] = []
    error: str = ""


@router.get("/tools")
def tools() -> list[str]:
    return list(DEFAULT_TOOLS)


@router.post("")
async def start(body: AgentTurnRequest, state: State) -> AgentTurnStarted:
    assert state.chat_agents is not None
    run_id = await state.chat_agents.start(
        body.conversation_id, body.content, body.tools, body.model_id, body.params
    )
    return AgentTurnStarted(run_id=run_id)


@router.post("/{run_id}/stop")
async def stop(run_id: str, state: State) -> AgentTurnStarted:
    assert state.chat_agents is not None
    state.chat_agents.cancel(run_id)
    return AgentTurnStarted(run_id=run_id)


@router.get("/{run_id}")
def follow(run_id: str, state: State) -> AgentTurn:
    assert state.chat_agents is not None
    with state.db.session() as conn:
        run = repo.agents.get_run(conn, run_id)
        if run is None:
            raise NotFound("Agent turn")
        calls = repo.tools.for_run(conn, run_id)
    turn = state.chat_agents.turns.get(run_id)
    return AgentTurn(
        run_id=run_id,
        status=run.status,
        live_run_id=turn.live_run_id if turn else "",
        calls=calls,
        error=run.error,
    )
