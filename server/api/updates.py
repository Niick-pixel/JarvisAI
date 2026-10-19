"""New versions of the app: what is available, fetching it, and handing over to the installer."""

from __future__ import annotations

from fastapi import APIRouter

from server.deps import State
from server.models.updates import UpdatePrefs, UpdateStatus

router = APIRouter(prefix="/api/updates", tags=["updates"])

# download and install start background work, so they are async: a plain `def` route runs in a
# worker thread, which has no event loop to start a task on.


@router.get("")
def status(state: State) -> UpdateStatus:
    assert state.updater is not None
    return state.updater.status


@router.post("/check")
async def check(state: State) -> UpdateStatus:
    """Ask GitHub for the newest release now, whether or not automatic updates are on."""
    assert state.updater is not None
    # With automatic updates on, a found version starts downloading right away - checking and
    # then waiting a day for the background loop to fetch it read as "nothing happens".
    return await state.updater.check(fetch=state.updater.status.auto)


@router.post("/download")
async def download(state: State) -> UpdateStatus:
    assert state.updater is not None
    return state.updater.download()


@router.post("/install")
async def install(state: State) -> UpdateStatus:
    """Runs the verified installer silently and closes the window; it reopens on the new version."""
    assert state.updater is not None
    return state.updater.install()


@router.put("/prefs")
def prefs(body: UpdatePrefs, state: State) -> UpdateStatus:
    assert state.updater is not None
    return state.updater.set_auto(body.auto)
