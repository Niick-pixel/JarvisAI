"""What the briefing knows, gathered as plain facts before any model sees them.

Each section is read-only and best-effort: no data, no section. A briefing that says "your ES data
is three days old" is more useful than one that quietly leaves markets out, so staleness is a fact
too.
"""

from __future__ import annotations

import asyncio
import logging
import time

from server.db import repo
from server.db.connection import Database
from server.forecast import engine, runs, store
from server.forecast.ninjatrader import Bar
from server.home.client import HomeError
from server.home.hub import Hub
from server.models.home import Device
from server.settings import Settings

log = logging.getLogger("jarvis.briefing")

SYMBOLS = ("ES", "NQ")
DAY = 86_400
HORIZON = 12
"""An hour ahead in five-minute bars: long enough to plan around, short enough to mean much."""


def _ago(seconds: float) -> str:
    if seconds < 3600:
        return f"{int(seconds // 60)} minutes ago"
    if seconds < 2 * DAY:
        return f"{int(seconds // 3600)} hours ago"
    return f"{int(seconds // DAY)} days ago"


def _change(bars: list[Bar]) -> str:
    last = bars[-1]
    before = next((b for b in reversed(bars) if b.t <= last.t - DAY), None)
    if before is None or not before.c:
        return ""
    pct = (last.c - before.c) / before.c * 100
    return f", {last.c - before.c:+.2f} ({pct:+.2f}%) over 24 hours"


async def markets(settings: Settings) -> str:
    shared = engine.shared(settings)
    ready = shared.status()
    lines: list[str] = []
    for symbol in SYMBOLS:
        with Database(settings.paths.db_path).session() as conn:
            series = store.series(conn, symbol)
        if not series.bars:
            continue
        last = series.bars[-1]
        line = (
            f"{symbol}: last close {last.c:.2f}, bar ending {_ago(time.time() - last.t)}"
            f"{_change(series.bars)}."
        )
        if ready.runtime and ready.weights:
            try:
                result = await asyncio.to_thread(
                    runs.forecast, shared, series, HORIZON, lambda *_: None
                )
                line += f" Forecast for the next hour: {result.summary}"
            except Exception as exc:  # noqa: BLE001 - a failed forecast is a fact, not a crash
                line += f" Forecast unavailable: {exc}"
        lines.append(line)
    return "\n".join(lines)


def _home_lines(found: list[Device]) -> list[str]:
    lines: list[str] = []
    lit = [d for d in found if d.domain == "light" and d.state == "on"]
    if lit:
        lines.append("Lights on: " + ", ".join(f"{d.name} ({d.area})" for d in lit[:8]))
    unlocked = [d.name for d in found if d.domain == "lock" and d.state == "unlocked"]
    if unlocked:
        lines.append("Unlocked: " + ", ".join(unlocked))
    open_ = [d.name for d in found if d.domain == "cover" and d.state == "open"]
    if open_:
        lines.append("Open: " + ", ".join(open_))
    for d in found:
        if d.domain == "climate" and d.current is not None:
            target = f", set to {d.target:g}" if d.target is not None else ""
            lines.append(f"{d.name}: {d.current:g}{d.unit}{target} ({d.state})")
    offline = [d.name for d in found if not d.available]
    if offline:
        lines.append(f"Not responding: {', '.join(offline[:6])}")
    return lines


async def home(hub: Hub | None) -> str:
    if hub is None:
        return ""
    try:
        if not (await hub.status()).connected:
            return ""
        found = await hub.devices()
    except HomeError as exc:
        return f"Home Assistant could not be reached: {exc}"
    lines = _home_lines(found)
    return "\n".join(lines) or f"All quiet: {len(found)} devices, nothing on or open."


def agents(db: Database, since_ms: int) -> str:
    with db.session() as conn:
        items = [
            i for i in repo.agents.list_inbox(conn) if i.created_at > since_ms and not i.read_at
        ]
    return "\n".join(
        f"{i.title}: {i.body.strip().splitlines()[0][:200]}" for i in items[:6] if i.body
    )
