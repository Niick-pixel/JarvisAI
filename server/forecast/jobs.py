"""One forecast or backtest at a time, in the background, with progress the sheet can poll.

A forecast takes seconds to a minute on the CPU - too long to hold a request open, and long
enough that "it is on step 9 of 24" is worth showing.
"""

from __future__ import annotations

import asyncio
import logging

from server.db.connection import Database
from server.forecast import runs, store
from server.forecast.engine import Engine
from server.models.forecast import ForecastJob


class ForecastJobs:
    def __init__(self, db: Database, engine: Engine) -> None:
        self.db = db
        self.engine = engine
        self.job = ForecastJob()
        self._task: asyncio.Task[None] | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def forecast(self, symbol: str, horizon: int) -> ForecastJob:
        return self._start("forecast", symbol, horizon, 0)

    def backtest(self, symbol: str, horizon: int, windows: int) -> ForecastJob:
        return self._start("backtest", symbol, horizon, windows)

    def _start(self, kind: str, symbol: str, horizon: int, windows: int) -> ForecastJob:
        if self.busy:
            return self.job
        # The last forecast and the last backtest both stay on screen while the other one runs.
        self.job = self.job.model_copy(
            update={
                "state": "loading",
                "kind": kind,
                "symbol": symbol,
                "step": 0,
                "total": 0,
                "detail": "Loading Kronos",
            }
        )
        self._task = asyncio.get_running_loop().create_task(
            self._run(kind, symbol, horizon, windows)
        )
        return self.job

    async def _run(self, kind: str, symbol: str, horizon: int, windows: int) -> None:
        def on_step(step: int, total: int) -> None:
            self._update(state="running", step=step, total=total, detail="")

        try:
            with self.db.session() as conn:
                series = store.series(conn, symbol)
            if kind == "forecast":
                result = await asyncio.to_thread(
                    runs.forecast, self.engine, series, horizon, on_step
                )
                self._update(state="done", forecast=result, detail="")
            else:
                scored = await asyncio.to_thread(
                    runs.backtest, self.engine, series, horizon, windows, on_step
                )
                self._update(state="done", backtest=scored, detail="")
        except (ValueError, OSError, RuntimeError, ImportError) as exc:
            logging.exception("forecast %s failed", kind)
            self._update(state="failed", detail=str(exc))

    def _update(self, **fields: object) -> None:
        self.job = self.job.model_copy(update=fields)
