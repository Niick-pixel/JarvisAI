"""Files: folders you opened, their contents, your own edits and Jarvis's, reviewed hunk by hunk."""

from __future__ import annotations

from fastapi import APIRouter

from server.chat.run import resolve_model_id
from server.deps import State
from server.errors import SovereignError
from server.files.docs import Unreadable
from server.files.propose import Proposals, TooLarge
from server.files.workspace import Workspace
from server.models.files import (
    ApplyRequest,
    Entry,
    FileContent,
    FileRef,
    Proposal,
    ProposeRequest,
    Root,
    RootCreate,
    RunRequest,
    RunResult,
    SaveRequest,
)
from server.providers.base import ProviderError
from server.tools.sandbox import Denied

router = APIRouter(prefix="/api/files", tags=["files"])


def _parts(state: State) -> tuple[Workspace, Proposals]:
    assert state.files is not None
    return state.files.workspace, state.files


def _refused(exc: Exception) -> SovereignError:
    return SovereignError("invalid_request", str(exc))


@router.get("/roots")
def roots(state: State) -> list[Root]:
    return _parts(state)[0].roots()


@router.post("/roots")
def add_root(body: RootCreate, state: State) -> Root:
    try:
        return _parts(state)[0].add_root(body.path)
    except Denied as exc:
        raise _refused(exc) from exc


@router.delete("/roots/{root_id}")
def remove_root(root_id: str, state: State) -> list[Root]:
    """Closes the folder in Files. Nothing on disk is touched."""
    workspace = _parts(state)[0]
    workspace.remove_root(root_id)
    return workspace.roots()


@router.get("/list")
def list_folder(root: str, state: State, path: str = "") -> list[Entry]:
    try:
        return _parts(state)[0].listing(root, path)
    except (Denied, OSError) as exc:
        raise _refused(exc) from exc


@router.get("/read")
def read(root: str, path: str, state: State) -> FileContent:
    try:
        return _parts(state)[0].read(root, path)
    except (Denied, Unreadable, OSError) as exc:
        raise _refused(exc) from exc


@router.put("/write")
def write(body: SaveRequest, state: State) -> FileContent:
    """Your own edit. Refused if the file changed on disk since you opened it."""
    try:
        return _parts(state)[0].write(body.root, body.path, body.version, body.text)
    except (Denied, Unreadable, OSError) as exc:
        raise _refused(exc) from exc


@router.post("/undo")
def undo(body: FileRef, state: State) -> FileContent:
    try:
        return _parts(state)[0].undo(body.root, body.path)
    except (Denied, OSError) as exc:
        raise _refused(exc) from exc


@router.post("/propose")
async def propose(body: ProposeRequest, state: State) -> Proposal:
    """Ask the model for a change. Nothing is written until you apply the proposal."""
    model_id = await resolve_model_id(state.db, state.registry, state.settings, body.model_id)
    if model_id is None:
        raise SovereignError("provider_unavailable", "No model is loaded to make the change.")
    try:
        return await _parts(state)[1].propose(body, model_id)
    except (Denied, Unreadable, TooLarge, OSError) as exc:
        raise _refused(exc) from exc
    except ProviderError as exc:
        raise SovereignError("provider_unavailable", str(exc)) from exc


@router.post("/proposals/{proposal_id}/apply")
def apply(proposal_id: str, body: ApplyRequest, state: State) -> FileContent:
    try:
        return _parts(state)[1].apply(proposal_id, body.hunks)
    except (Denied, Unreadable, OSError) as exc:
        raise _refused(exc) from exc


@router.delete("/proposals/{proposal_id}")
def discard(proposal_id: str, state: State) -> dict[str, str]:
    _parts(state)[1].discard(proposal_id)
    return {"status": "discarded"}


@router.post("/run")
async def run(body: RunRequest, state: State) -> RunResult:
    """Runs exactly the command you typed, in the folder, when you press Run."""
    if not body.command.strip():
        raise SovereignError("invalid_request", "Type a command to run.")
    try:
        return await _parts(state)[0].run(body.root, body.command)
    except (Denied, OSError) as exc:
        raise _refused(exc) from exc
