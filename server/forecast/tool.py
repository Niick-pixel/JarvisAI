"""`forecast` for agents: a scheduled job can forecast ES and NQ every morning and write up what
it sees. Read-only - it looks at data you imported and changes nothing - so it needs no approval.
"""

from __future__ import annotations

import asyncio

from server.db.connection import Database
from server.forecast import engine, runs, store
from server.tools.builtin import ToolContext, ToolResult
from server.tools.sandbox import Denied

HORIZONS = (6, 12, 24, 48)


async def forecast(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    symbol = str(args.get("symbol", "")).upper()
    try:
        horizon = int(str(args.get("horizon", 12)))
    except ValueError as exc:
        raise Denied("horizon is a number of five-minute bars: 6, 12, 24 or 48.") from exc
    if horizon not in HORIZONS:
        raise Denied("horizon is a number of five-minute bars: 6, 12, 24 or 48.")
    shared = engine.shared(ctx.settings)
    status = shared.status()
    if not (status.runtime and status.weights):
        raise Denied(f"Forecasting is not set up: {status.reason}")
    with Database(ctx.settings.paths.db_path).session() as conn:
        series = store.series(conn, symbol)
    if not series.bars:
        raise Denied(
            f"No {symbol} data has been imported. Import a NinjaTrader export in Forecast."
        )
    try:
        result = await asyncio.to_thread(runs.forecast, shared, series, horizon, lambda *_: None)
    except runs.NotEnoughData as exc:
        raise Denied(str(exc)) from exc
    return ToolResult(result.summary, f"{symbol} {horizon} bars")
