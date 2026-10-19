"""The morning briefing: when it comes, what it covers, and the latest one."""

from __future__ import annotations

from fastapi import APIRouter

from server.briefing import service
from server.deps import AppState, State
from server.models.briefing import Briefing, BriefingSettings

router = APIRouter(prefix="/api/briefing", tags=["briefing"])
KEY = "briefing"


def schedule(state: AppState) -> None:
    """Put the briefing on the clock - or take it off - to match its settings."""
    if state.scheduler is None or state.briefings is None:
        return
    value = service.load_settings(state.db)
    cron = service.cron_for(value) if value.enabled else None
    state.scheduler.builtin(KEY, cron, state.briefings.run)


@router.get("/settings")
def get_settings(state: State) -> BriefingSettings:
    value = service.load_settings(state.db)
    next_at = state.scheduler.next_run_at(f"builtin:{KEY}") if state.scheduler else None
    return value.model_copy(update={"next_at": next_at})


@router.put("/settings")
def put_settings(body: BriefingSettings, state: State) -> BriefingSettings:
    service.save_settings(state.db, body)
    schedule(state)
    return get_settings(state)


@router.post("/run")
async def run_now(state: State) -> Briefing:
    assert state.briefings is not None
    return await state.briefings.run()


@router.get("/latest")
def latest(state: State) -> Briefing | None:
    found = service.latest(state.db)
    return found[0] if found else None


@router.post("/{briefing_id}/read")
def read(briefing_id: str, state: State) -> None:
    service.mark_read(state.db, briefing_id)
