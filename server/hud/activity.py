"""Everything Jarvis is doing that you are not looking at, in one list - so a busy fan or a slow
answer always has a visible reason. Read once a second by the HUD stream; nothing here waits."""

from __future__ import annotations

import time

from server.deps import AppState
from server.models.hud import Activity


def _fraction(done: int, total: int | None) -> float | None:
    return min(1.0, done / total) if total else None


def collect(state: AppState) -> list[Activity]:
    out: list[Activity] = []
    llama = state.llama.status if state.llama else None
    if llama and llama.loading:
        elapsed = time.time() - llama.load_started_at
        expected = llama.load_expected_s
        out.append(
            Activity(
                kind="model",
                label=f"Loading {llama.model_path.replace(chr(92), '/').split('/')[-1]}",
                detail=llama.load_stage,
                # An estimate, so it never claims to be finished: it stops at 95% until it is.
                progress=min(0.95, elapsed / expected) if expected else None,
                seconds=round(elapsed),
            )
        )
    if live := len(state.live.active_ids()):
        out.append(Activity(kind="answer", label="Answering" if live == 1 else f"{live} answers"))
    for name, pack in (
        ("model", state.downloader),
        ("voice", state.voice_pack),
        ("voice", state.kokoro_pack),
    ):
        fetch = pack.progress if pack else None
        if fetch and fetch.state in ("resolving", "downloading", "verifying"):
            title = getattr(fetch, "display_name", "") or getattr(fetch, "file", "")
            out.append(
                Activity(
                    kind="download",
                    label=f"Downloading {title or name}",
                    detail="Checking the file" if fetch.state == "verifying" else "",
                    progress=_fraction(fetch.bytes_done, fetch.bytes_total),
                )
            )
    if state.images and state.images.state in ("installing", "generating"):
        making = state.images.state == "generating"
        out.append(
            Activity(
                kind="image",
                label="Making a picture" if making else "Setting up pictures",
                detail=state.images.detail,
                progress=_fraction(state.images.step, state.images.total) if making else None,
            )
        )
    for index in state.indexer.progress.values():
        if index.state in ("scanning", "chunking", "embedding"):
            out.append(
                Activity(
                    kind="index",
                    label="Reading your documents",
                    detail=index.detail,
                    progress=_fraction(index.files_done, index.files_total),
                )
            )
    if state.updater and state.updater.status.state == "downloading":
        status = state.updater.status
        out.append(
            Activity(
                kind="update",
                label=f"Downloading Jarvis {status.latest}",
                progress=_fraction(status.bytes_done, status.bytes_total),
            )
        )
    if state.forecasts and state.forecasts.busy:
        out.append(Activity(kind="forecast", label="Running a forecast"))
    agents = state.chat_agents
    if agents and any(state.approvals.is_driving(run_id) for run_id in agents.turns):
        out.append(Activity(kind="agent", label="Agent working in a chat"))
    return out
