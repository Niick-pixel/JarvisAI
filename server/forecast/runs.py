"""A forecast and a backtest, turned from sampled paths into numbers a trader reads.

The backtest exists because a forecast with no track record is a guess with a chart. It hides
the end of your own data, forecasts it from what came before, and scores the result against what
actually happened - and against the forecast every model has to beat, "the price will not move".
"""

from __future__ import annotations

import time

import numpy as np

from server.forecast.describe import describe
from server.forecast.engine import Engine, OnStep, Window
from server.forecast.sessions import next_bar_ends
from server.forecast.store import Series
from server.models.forecast import (
    BacktestResult,
    BacktestRow,
    Candle,
    ForecastResult,
    ForecastStep,
)

HISTORY_BARS = 144
"""Twelve hours of five-minute bars on the chart before the forecast starts."""
SHOWN_PATHS = 12
# Tick size and dollars per tick, per contract.
TICKS = {"ES": (0.25, 12.5), "NQ": (0.25, 5.0), "MES": (0.25, 1.25), "MNQ": (0.25, 0.5)}


class NotEnoughData(ValueError):
    pass


def _need(series: Series, bars: int) -> None:
    if len(series.bars) < bars:
        raise NotEnoughData(
            f"{series.symbol} has {len(series.bars)} five-minute bars; this needs at least {bars}. "
            "Import a longer export."
        )


def forecast(engine: Engine, series: Series, horizon: int, on_step: OnStep) -> ForecastResult:
    cfg = engine.settings.forecast
    _need(series, min(cfg.lookback, 120))
    started = time.monotonic()
    bars = series.bars[-cfg.lookback :]
    last = bars[-1]
    future = next_bar_ends(last.t, horizon)
    samples = engine.sample([Window(bars, future)], horizon, cfg.paths, on_step)[0]
    ohlc = np.median(samples[:, :, :4], axis=0)
    closes = samples[:, :, 3]
    low_band, high_band = np.percentile(closes, [10, 90], axis=0)
    steps = []
    for i, t in enumerate(future):
        o, h, low, c = (float(v) for v in ohlc[i])
        # Medians taken column by column can cross; a candle cannot.
        h, low = max(h, o, c), min(low, o, c)
        steps.append(
            ForecastStep(t=t, o=o, h=h, l=low, c=c, p10=float(low_band[i]), p90=float(high_band[i]))
        )
    tick, value = TICKS.get(series.symbol, (0.25, 0.0))
    notes = list(series.rolls[-1:])
    if future and future[-1] - last.t > horizon * 300 + 3600:
        notes.append("The forecast crosses a halt or a weekend; the gap is not drawn.")
    result = ForecastResult(
        symbol=series.symbol,
        horizon=horizon,
        made_at=int(time.time()),
        last_t=last.t,
        last_close=last.c,
        history=[
            Candle(t=b.t, o=b.o, h=b.h, l=b.low, c=b.c, v=b.v) for b in series.bars[-HISTORY_BARS:]
        ],
        steps=steps,
        paths=[[round(float(v), 2) for v in path] for path in closes[:SHOWN_PATHS]],
        prob_up=float(np.mean(closes[:, -1] > last.c)),
        median_move=float(np.median(closes[:, -1]) - last.c),
        tick_size=tick,
        tick_value=value,
        elapsed_ms=int((time.monotonic() - started) * 1000),
        model=cfg.model,
        notes=notes,
    )
    return result.model_copy(update={"summary": describe(result)})


def backtest(
    engine: Engine, series: Series, horizon: int, windows: int, on_step: OnStep
) -> BacktestResult:
    cfg = engine.settings.forecast
    lookback = min(cfg.lookback, 256)  # shorter context keeps a dozen forecasts to minutes
    _need(series, lookback + horizon + windows)
    started = time.monotonic()
    bars = series.bars
    # Evenly spaced over the history, so it is not judged on one week's market.
    cutoffs = np.linspace(lookback - 1, len(bars) - horizon - 1, windows).astype(int)
    batch = [
        Window(bars[c - lookback + 1 : c + 1], [b.t for b in bars[c + 1 : c + 1 + horizon]])
        for c in cutoffs
    ]
    samples = engine.sample(batch, horizon, cfg.backtest_paths, on_step)
    rows = []
    for c, paths in zip(cutoffs, samples, strict=True):
        ends = paths[:, -1, 3]
        p10, p90 = np.percentile(ends, [10, 90])
        rows.append(
            BacktestRow(
                t=bars[c].t,
                last=bars[c].c,
                actual=bars[c + horizon].c,
                median=float(np.median(ends)),
                p10=float(p10),
                p90=float(p90),
            )
        )
    return score(rows, series.symbol, horizon, int((time.monotonic() - started) * 1000), cfg.model)


def score(
    rows: list[BacktestRow], symbol: str, horizon: int, elapsed_ms: int, model: str
) -> BacktestResult:
    moved = [r for r in rows if r.actual != r.last]
    hits = [np.sign(r.median - r.last) == np.sign(r.actual - r.last) for r in moved]
    mae_model = float(np.mean([abs(r.median - r.actual) for r in rows]))
    mae_naive = float(np.mean([abs(r.last - r.actual) for r in rows]))
    return BacktestResult(
        symbol=symbol,
        horizon=horizon,
        windows=len(rows),
        hit_rate=float(np.mean(hits)) if hits else 0.0,
        mae_model=mae_model,
        mae_naive=mae_naive,
        skill=1 - mae_model / mae_naive if mae_naive else 0.0,
        coverage=float(np.mean([r.p10 <= r.actual <= r.p90 for r in rows])),
        rows=rows,
        elapsed_ms=elapsed_ms,
        model=model,
    )
