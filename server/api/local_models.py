"""Managing the model files on this PC: see them, switch the engine to one, delete one.

Deleting is the only irreversible thing here, so it is narrow: only a file inside the models
folder, only through this endpoint, and if that file is the one being served the engine is
moved to the next best model first, rather than left pointing at nothing.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from server.db import repo
from server.deps import State
from server.errors import SovereignError
from server.models.library import LocalModel, LocalModels
from server.providers import launch_args

router = APIRouter(prefix="/api/models/local", tags=["models"])


def _inside(path: Path, folder: Path) -> bool:
    try:
        return path.resolve().is_relative_to(folder.resolve())
    except OSError:
        return False


def _library(state: State) -> LocalModels:
    folder = state.settings.paths.models_dir
    loaded = state.llama.status.model_path if state.llama else ""
    with state.db.session() as conn:
        found = launch_args.registered_models(conn, folder)
        pinned = repo.settings.get(conn, repo.settings.SELECTED_MODEL)
    models = [
        LocalModel(
            id=m.id,
            display_name=m.display_name,
            file_path=m.file_path or "",
            size_bytes=m.size_bytes or 0,
            quant=m.quant,
            loaded=bool(loaded) and Path(loaded) == Path(m.file_path or ""),
            pinned=m.id == pinned,
            deletable=_inside(Path(m.file_path or ""), folder),
        )
        for m in found
    ]
    return LocalModels(
        models=models, folder=str(folder), total_bytes=sum(m.size_bytes for m in models)
    )


def _find(state: State, model_id: str) -> LocalModel:
    found = next((m for m in _library(state).models if m.id == model_id), None)
    if found is None:
        raise SovereignError("not_found", "That model is not on this PC any more.", status_code=404)
    return found


@router.get("")
def library(state: State) -> LocalModels:
    return _library(state)


@router.post("/{model_id}/use")
async def use(model_id: str, state: State) -> LocalModels:
    """Serve this model now: pin it and restart the engine on it."""
    _find(state, model_id)
    with state.db.session() as conn:
        repo.settings.put(conn, repo.settings.SELECTED_MODEL, model_id)
    if state.llama is not None:
        await state.llama.restart()
    return _library(state)


@router.delete("/{model_id}")
async def delete(model_id: str, state: State) -> LocalModels:
    model = _find(state, model_id)
    if not model.deletable:
        raise SovereignError(
            "invalid_request",
            f"{model.file_path} is outside the models folder, so Jarvis will not delete it.",
        )
    if model.loaded and state.llama is not None:
        await state.llama.stop()  # Windows will not delete a file a process has open
    with state.db.session() as conn:
        if model.pinned:
            repo.settings.clear(conn, repo.settings.SELECTED_MODEL)
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
    Path(model.file_path).unlink(missing_ok=True)
    if model.loaded and state.llama is not None:
        await state.llama.start()  # the next best model this PC has, if any
    return _library(state)
