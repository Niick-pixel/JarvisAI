"""1 Hz telemetry for the HUD: the machine, the model, and everything running in the background."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path

from server.chat.live import TOKENS
from server.deps import AppState
from server.hardware import probe
from server.hud import activity
from server.models.hud import HudSample

INTERVAL_S = 1.0


def sample(state: AppState, tokens_per_second: float = 0.0) -> HudSample:
    import psutil

    gpus, _ = probe.probe_gpus()
    memory = psutil.virtual_memory()
    llama = state.llama.status if state.llama else None
    serving = llama is not None and llama.started and not llama.loading
    return HudSample(
        gpu=gpus[0] if gpus else None,
        ram_used_mb=(memory.total - memory.available) // (1024 * 1024),
        ram_total_mb=memory.total // (1024 * 1024),
        # Since the previous call: the first sample of a stream reads 0, never a fake number.
        cpu_percent=psutil.cpu_percent(interval=None),
        tokens_per_second=tokens_per_second,
        active_runs=len(state.live.active_ids()),
        model=Path(llama.model_path).name if serving and llama else "",
        activity=activity.collect(state),
    )


async def stream(state: AppState) -> AsyncIterator[dict[str, str]]:
    last_count, last_at = TOKENS.count, time.monotonic()
    while True:
        now = time.monotonic()
        rate = (TOKENS.count - last_count) / max(now - last_at, 1e-3)
        last_count, last_at = TOKENS.count, now
        yield {"event": "hud", "data": sample(state, round(rate, 1)).model_dump_json()}
        await asyncio.sleep(INTERVAL_S)
