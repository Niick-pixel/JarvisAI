"""Futures forecasting: import NinjaTrader exports, forecast ES and NQ, check the track record."""

from __future__ import annotations

from fastapi import APIRouter, Request

from server.deps import State
from server.errors import SovereignError
from server.forecast import ninjatrader, store
from server.models.forecast import (
    BacktestRequest,
    ForecastJob,
    ForecastRequest,
    ForecastStatus,
    ImportResult,
    SeriesInfo,
)
from server.models.voice import VoicePackProgress

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

MAX_IMPORT_MB = 200
HORIZONS = (6, 12, 24, 48)


@router.get("/status")
def status(state: State) -> ForecastStatus:
    assert state.forecasts is not None
    return state.forecasts.engine.status()


@router.get("/series")
def series(state: State) -> list[SeriesInfo]:
    with state.db.session() as conn:
        return store.summary(conn)


@router.post("/import")
async def import_file(
    request: Request, state: State, filename: str, symbol: str = ""
) -> ImportResult:
    """The export itself as the request body, its name in the query: the name is where the
    market and contract month come from (`ES 03-25.Last.txt`)."""
    body = await request.body()
    if len(body) > MAX_IMPORT_MB * 1_000_000:
        raise SovereignError("invalid_request", f"That file is over {MAX_IMPORT_MB}MB.")
    try:
        parsed = ninjatrader.parse(body.decode("utf-8-sig", errors="replace"), filename, symbol)
        with state.db.session() as conn:
            return store.save(conn, parsed, filename)
    except ValueError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc


@router.delete("/series/{symbol}")
def clear(symbol: str, state: State) -> list[SeriesInfo]:
    with state.db.session() as conn:
        store.clear(conn, symbol.upper())
        return store.summary(conn)


# The routes that start background work are async on purpose: a plain `def` route runs in a worker
# thread, where there is no event loop to start the task on.


def _ready(state: State) -> None:
    assert state.forecasts is not None
    engine = state.forecasts.engine.status()
    if not (engine.runtime and engine.weights):
        raise SovereignError("provider_unavailable", engine.reason)


@router.post("/run")
async def run(body: ForecastRequest, state: State) -> ForecastJob:
    assert state.forecasts is not None
    if body.horizon not in HORIZONS:
        raise SovereignError("invalid_request", f"Horizon must be one of {HORIZONS} bars.")
    _ready(state)
    return state.forecasts.forecast(body.symbol.upper(), body.horizon)


@router.post("/backtest")
async def backtest(body: BacktestRequest, state: State) -> ForecastJob:
    assert state.forecasts is not None
    if body.horizon not in HORIZONS or not 4 <= body.windows <= 48:
        raise SovereignError("invalid_request", "Pick a listed horizon and 4 to 48 windows.")
    _ready(state)
    return state.forecasts.backtest(body.symbol.upper(), body.horizon, body.windows)


@router.get("/job")
def job(state: State) -> ForecastJob:
    assert state.forecasts is not None
    return state.forecasts.job


@router.get("/pack")
def pack_progress(state: State) -> VoicePackProgress:
    assert state.forecast_pack is not None
    return state.forecast_pack.progress


@router.post("/pack")
async def pack_start(state: State) -> VoicePackProgress:
    """Fetch the Kronos model and its tokenizer from Hugging Face - only now, only these."""
    assert state.forecast_pack is not None
    return state.forecast_pack.start()
