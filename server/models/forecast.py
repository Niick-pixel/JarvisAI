"""Futures forecasting: imported data, a forecast, a backtest, and what the engine needs to run.

Times are UTC epoch seconds at which a bar ends - the label NinjaTrader puts on a bar.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ImportResult(BaseModel):
    symbol: str
    contract: str
    """"03-25", or "" when the file was already a continuous series."""
    filename: str
    rows: int
    """Lines read from the file, before rolling one-minute bars up into five."""
    bars: int
    first: int
    last: int
    zone: str
    """The time zone the file's times were read in, as people say it: "US Central"."""
    zone_assumed: bool
    """True when the file did not show it, so US Central was assumed. Worth checking."""
    source_minutes: int
    stamps: Literal["bar end", "bar start"]
    notes: list[str] = []


class SeriesInfo(BaseModel):
    symbol: str
    bars: int
    first: int
    last: int
    contracts: list[str]
    zone: str
    zone_assumed: bool


class Candle(BaseModel):
    t: int
    o: float
    h: float
    l: float  # noqa: E741 - the chart's own letter for low
    c: float
    v: float = 0.0


class ForecastStep(BaseModel):
    t: int
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    """The median path: the middle of what the samples did, not one sample."""
    p10: float
    p90: float
    """Eight in ten sampled paths closed this bar between p10 and p90."""


class ForecastResult(BaseModel):
    symbol: str
    horizon: int
    """Bars ahead. At five minutes a bar, 12 is an hour."""
    made_at: int
    last_t: int
    last_close: float
    history: list[Candle]
    steps: list[ForecastStep]
    paths: list[list[float]]
    """Each sampled path's closes, for drawing the spread as faint lines."""
    prob_up: float
    """Share of sampled paths that end above the last close."""
    median_move: float
    tick_size: float
    tick_value: float
    """Dollars per tick per contract."""
    elapsed_ms: int
    model: str
    summary: str = ""
    """The forecast in one paragraph of plain numbers: what "Ask Jarvis" sends, and what an
    agent's forecast tool returns."""
    notes: list[str] = []


class BacktestRow(BaseModel):
    t: int
    """When the forecast was made: the last bar it could see."""
    last: float
    actual: float
    median: float
    p10: float
    p90: float


class BacktestResult(BaseModel):
    symbol: str
    horizon: int
    windows: int
    hit_rate: float
    """How often the median path called the direction right (flat outcomes not counted)."""
    mae_model: float
    mae_naive: float
    """Mean error of "the price will not move", the bar every forecast has to clear."""
    skill: float
    """1 - mae_model / mae_naive. Above zero beats doing nothing; below zero is worse."""
    coverage: float
    """How often the outcome landed inside p10-p90. A calibrated forecast is near 0.8."""
    rows: list[BacktestRow]
    elapsed_ms: int
    model: str


JobState = Literal["idle", "loading", "running", "done", "failed"]


class ForecastJob(BaseModel):
    state: JobState = "idle"
    kind: Literal["forecast", "backtest"] = "forecast"
    symbol: str = ""
    step: int = 0
    total: int = 0
    detail: str = ""
    forecast: ForecastResult | None = None
    backtest: BacktestResult | None = None


class ForecastRequest(BaseModel):
    symbol: str
    horizon: int = 12


class BacktestRequest(BaseModel):
    symbol: str
    horizon: int = 12
    windows: int = 12


class ForecastStatus(BaseModel):
    runtime: bool
    """PyTorch is importable. False in a copy installed without the forecast extra."""
    weights: bool
    model: str
    expected_path: str
    reason: str = ""
    fix: str = ""
    device: str = "cpu"
    threads: int = 0
