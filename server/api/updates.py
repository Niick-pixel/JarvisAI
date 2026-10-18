"""New versions of the app: what is available, fetching it, and handing over to the installer."""

from __future__ import annotations

from fastapi import APIRouter

from server.deps import State
from server.models.updates import UpdatePrefs, UpdateStatus

router = APIRouter(prefix="/api/updates", tags=["updates"])


@router.get("")
def status(state: State) -> UpdateStatus:
    assert state.updater is not None
    return state.updater.status


@router.post("/check")
async def check(state: State) -> UpdateStatus:
    """Ask GitHub for the newest release now, whether or not automatic updates are on."""
    assert state.updater is not None
    return await state.updater.check()


@router.post("/download")
def download(state: State) -> UpdateStatus:
    assert state.updater is not None
    return state.updater.download()


@router.post("/install")
def install(state: State) -> UpdateStatus:
    """Runs the verified installer silently and closes the window; it reopens on the new version."""
    assert state.updater is not None
    return state.updater.install()


@router.put("/prefs")
def prefs(body: UpdatePrefs, state: State) -> UpdateStatus:
    assert state.updater is not None
    return state.updater.set_auto(body.auto)
