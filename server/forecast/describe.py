"""A forecast in words, for a language model to reason about and a person to skim."""

from __future__ import annotations

from server.forecast.sessions import exchange_time
from server.models.forecast import ForecastResult


def _clock(t: int) -> str:
    return exchange_time(t).strftime("%a %H:%M CT")


def describe(f: ForecastResult) -> str:
    end = f.steps[-1]
    minutes = f.horizon * 5
    span = f"{minutes // 60}h" if minutes % 60 == 0 else f"{minutes} min"
    ticks = round(f.median_move / f.tick_size) if f.tick_size else 0
    cash = ticks * f.tick_value
    dollars = f" ({'-' if cash < 0 else '+'}${abs(cash):,.2f} per contract)" if f.tick_value else ""
    when = f"from the {_clock(f.last_t)} close of {f.last_close:.2f} to {_clock(end.t)}"
    move = f"{f.median_move:+.2f} points or {ticks:+d} ticks{dollars}"
    band = f"{end.p10:.2f} and {end.p90:.2f}"
    return (
        f"{f.symbol} 5-minute Kronos forecast ({f.model}), {span} ahead, {when}. "
        f"Median path ends at {end.c:.2f}, {move}. "
        f"80% of the sampled paths stayed between {band} at the end. "
        f"{f.prob_up:.0%} of sampled paths finish above the last close. "
        "This is a statistical model of past price patterns, not trading advice."
    )
