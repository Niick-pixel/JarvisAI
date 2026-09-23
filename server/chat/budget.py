"""How much context a turn gets, and whether it will fit, decided before anything is written.

Split out of run.py. Both answers depend on whether the model is already resident: llama-server
fixes its context and allocates the memory at load, so for it the question is settled; Ollama
and LM Studio size per request, so for them it is still worth asking.
"""

from __future__ import annotations

from server.errors import SovereignError
from server.hardware import probe, recommend
from server.models.provider import ModelInfo
from server.models.stream import ChatRequest
from server.providers.base import ModelProvider
from server.settings import Settings

DEFAULT_CTX_FALLBACK = 4096


def resolve_ctx_len(request: ChatRequest, model: ModelInfo, settings: Settings) -> int:
    if request.ctx_len:
        return min(request.ctx_len, model.ctx_len_max or request.ctx_len)
    if model.provider == "llamacpp" and model.ctx_len_max:
        # llama-server fixes its context when it loads the model, and already holds the memory for
        # it. Recomputing from free VRAM now counts the loaded weights twice: that is how a server
        # started at 32K was being used at 8K, and why the composer read "6,144 tokens".
        return model.ctx_len_max
    gpus, _ = probe.probe_gpus()
    gpu = gpus[0] if gpus else None
    if gpu is None:
        return model.ctx_len_max or DEFAULT_CTX_FALLBACK
    return recommend.max_ctx_for(
        model,
        gpu=gpu,
        browser_reserve_mb=settings.hardware.browser_vram_reserve_mb,
        kv_dtype=settings.hardware.kv_cache_dtype,
    )


def preflight_vram(
    model: ModelInfo, ctx_len: int, settings: Settings, provider: ModelProvider
) -> None:
    """Refuse before the backend OOMs, and hand back the fix (BRIEF.md section 2)."""
    if provider.kind not in ("ollama", "lmstudio"):
        # llama.cpp: the model is resident and its context allocated - there is nothing left to
        # preflight, and measuring free VRAM now would count the loaded weights a second time.
        return
    gpus, _ = probe.probe_gpus()
    if not gpus:
        return
    budget = recommend.budget_for(
        model,
        ctx_len=ctx_len,
        gpu=gpus[0],
        browser_reserve_mb=settings.hardware.browser_vram_reserve_mb,
        kv_dtype=settings.hardware.kv_cache_dtype,
    )
    if budget.fits or model.size_bytes is None:
        # Without a real file size the estimate is too rough to refuse on; the backend decides.
        return
    raise SovereignError(
        "vram_insufficient",
        budget.explanation,
        remedy=budget.remedy,
        status_code=507,
    )
