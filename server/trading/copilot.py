"""The co-pilot's heartbeat: read new bars, re-forecast every few of them, check the alerts.

It runs as one background task. Every step is best-effort and logged: a feed file that cannot be
read or a forecast that fails must never stop the next poll.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from server.db.connection import Database
from server.forecast import engine, runs, store
from server.forecast.ninjatrader import Bar
from server.models.trading import AlertEvent, LiveStatus, LiveSymbol
from server.settings import Settings
from server.trading import alerts
from server.trading.feed import Feed, default_dir

log = logging.getLogger("jarvis.trading")
HORIZON = 12


@dataclass
class Rolling:
    summary: str
    prob_up: float
    made_at: int
    bars_since: int = 0


class Copilot:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        folder = settings.trading.feed_dir
        self.feed = Feed(Path(folder) if folder else default_dir())
        self.rolling: dict[str, Rolling] = {}
        self._busy: set[str] = set()

    def forecasting(self) -> bool:
        status = engine.shared(self.settings).status()
        return bool(status.runtime and status.weights)

    async def tick(self) -> list[AlertEvent]:
        """One poll: new bars in, forecasts where due, alerts judged. Returns what fired."""
        with self.db.session() as conn:
            fresh = self.feed.poll(conn)
        fired: list[AlertEvent] = []
        for symbol in set(fresh) | set(self.feed.latest):
            new = fresh.get(symbol, [])
            if new:
                await self._maybe_forecast(symbol, len(new))
            if new or self.feed.stale(symbol):
                fired += self.judge(symbol)
        return fired

    def _bars(self, symbol: str) -> list[Bar]:
        with self.db.session() as conn:
            return store.series(conn, symbol).bars

    def judge(self, symbol: str) -> list[AlertEvent]:
        bars = self._bars(symbol)[-alerts.RANGE_BARS :]
        rolling = self.rolling.get(symbol)
        with self.db.session() as conn:
            return alerts.check(
                conn,
                symbol,
                bars,
                prob_up=rolling.prob_up if rolling else None,
                stale=self.feed.stale(symbol),
            )

    async def _maybe_forecast(self, symbol: str, new_bars: int) -> None:
        rolling = self.rolling.get(symbol)
        if rolling:
            rolling.bars_since += new_bars
        due = rolling is None or rolling.bars_since >= self.settings.trading.forecast_every
        if not due or symbol in self._busy or not self.forecasting():
            return
        self._busy.add(symbol)
        try:
            with self.db.session() as conn:
                series = store.series(conn, symbol)
            shared = engine.shared(self.settings)
            result = await asyncio.to_thread(
                runs.forecast, shared, series, HORIZON, lambda *_: None
            )
            self.rolling[symbol] = Rolling(result.summary, result.prob_up, int(time.time() * 1000))
        except Exception as exc:  # noqa: BLE001 - the next bar tries again
            log.warning("rolling forecast for %s failed: %s", symbol, exc)
        finally:
            self._busy.discard(symbol)

    def status(self) -> LiveStatus:
        symbols = []
        for symbol, latest in sorted(self.feed.latest.items()):
            rolling = self.rolling.get(symbol)
            symbols.append(
                LiveSymbol(
                    symbol=symbol,
                    contract=latest.contract,
                    last_t=latest.t,
                    last_close=latest.close,
                    bars_received=latest.bars,
                    stale=self.feed.stale(symbol),
                    forecast=rolling.summary if rolling else "",
                    prob_up=rolling.prob_up if rolling else None,
                    forecast_at=rolling.made_at if rolling else None,
                )
            )
        with self.db.session() as conn:
            recent = alerts.events(conn)
        return LiveStatus(
            folder=str(self.feed.folder),
            folder_exists=self.feed.folder.is_dir(),
            files=[p.name for p in self.feed.files()],
            symbols=symbols,
            forecasting=self.forecasting(),
            events=recent,
        )

    async def run_forever(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001 - one bad poll must not end the loop
                log.warning("trading poll failed: %s", exc)
            await asyncio.sleep(self.settings.trading.poll_seconds)
