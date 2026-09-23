from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter

from server import paths
from server.db import repo
from server.deps import State
from server.errors import NotFound, SovereignError
from server.hardware import catalog as catalog_mod
from server.hardware import probe, recommend, registry_files
from server.models.hardware import (
    DownloadProgress,
    DownloadRequest,
    HardwareReport,
    ModelRecommendation,
    VramBudget,
)

router = APIRouter(prefix="/api/hardware", tags=["hardware"])
CATALOG_PATH = paths.resource("models.toml")


@router.get("")
def hardware(state: State) -> HardwareReport:
    return probe.report(state.settings.paths.models_dir)


@router.get("/budget")
async def budget(state: State, model_id: str, ctx_len: int) -> VramBudget:
    """The itemised VRAM table for one model at one context length. Shown in the UI, not hidden."""
    models = await state.registry.models()
    model = next((m for m in models if m.id == model_id), None)
    if model is None:
        raise NotFound("Model")
    gpus, _ = probe.probe_gpus()
    return recommend.budget_for(
        model,
        ctx_len=ctx_len,
        gpu=gpus[0] if gpus else None,
        browser_reserve_mb=state.settings.hardware.browser_vram_reserve_mb,
        kv_dtype=state.settings.hardware.kv_cache_dtype,
    )


@router.get("/catalog")
async def catalog(state: State) -> list[ModelRecommendation]:
    """The same ranking `make models` prints, with real sizes and what is already on disk."""
    gpus, _ = probe.probe_gpus()
    entries = catalog_mod.load_catalog(CATALOG_PATH)
    ranked = catalog_mod.rank_catalog(
        entries,
        gpu=gpus[0] if gpus else None,
        browser_reserve_mb=state.settings.hardware.browser_vram_reserve_mb,
        kv_dtype=state.settings.hardware.kv_cache_dtype,
    )
    by_key = {e["key"]: e for e in entries}
    # Sizes come from the registry, concurrently and cached for the process: the first open of
    # the download screen pays a second or two, never again. Offline leaves them unknown.
    resolved = await asyncio.gather(
        *(asyncio.to_thread(registry_files.resolve_file, by_key[r.key]) for r in ranked)
    )
    models_dir = state.settings.paths.models_dir
    return [
        rec.model_copy(
            update={
                "resolved_file": filename,
                "download_size_bytes": size,
                "installed": registry_files.installed_file(by_key[rec.key], models_dir) is not None,
            }
        )
        for rec, (filename, size, _) in zip(ranked, resolved, strict=True)
    ]


@router.get("/download")
def download_progress(state: State) -> DownloadProgress:
    assert state.downloader is not None
    return state.downloader.progress


@router.post("/download")
async def start_download(body: DownloadRequest, state: State) -> DownloadProgress:
    """Fetch one model from the catalogue, then serve it. Only catalogue keys are accepted."""
    assert state.downloader is not None
    if state.downloader.busy:
        raise SovereignError("invalid_request", "A model is already downloading.", status_code=409)
    entries = {e["key"]: e for e in catalog_mod.load_catalog(CATALOG_PATH)}
    entry = entries.get(body.key)
    if entry is None:
        raise NotFound("Catalogue entry")
    gpus, _ = probe.probe_gpus()
    rec = next(
        r
        for r in catalog_mod.rank_catalog(
            [entry],
            gpu=gpus[0] if gpus else None,
            browser_reserve_mb=state.settings.hardware.browser_vram_reserve_mb,
            kv_dtype=state.settings.hardware.kv_cache_dtype,
        )
    )

    async def serve_it() -> None:
        # What you just downloaded is what you meant to use: pin it, then (re)start llama-server
        # on it. A server you started yourself is still never touched.
        path = state.downloader.progress.path if state.downloader else ""
        with state.db.session() as conn:
            repo.settings.put(conn, repo.settings.SELECTED_MODEL, f"llamacpp:{Path(path).name}")
        if state.llama is not None:
            await state.llama.restart()
        await state.registry.refresh()

    return state.downloader.start(entry, rec.recommended_ctx_len, on_done=serve_it)


@router.delete("/download")
def cancel_download(state: State) -> DownloadProgress:
    """Stop it. The partial file stays, so starting again resumes instead of starting over."""
    assert state.downloader is not None
    state.downloader.cancel()
    return state.downloader.progress
