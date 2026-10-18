"""Bars in, bars out: saving imports, and reading one continuous series per market.

Contracts expire, so a year of ES is four or five contracts. Glued end to end, each roll would be
a jump of tens of points that never traded, and the model would learn to expect them. The series
here rolls on the first session the next contract trades more than the current one - when the
volume moves, which is when traders do - and shifts every earlier contract by the price
difference at the roll (back-adjusting), so the latest prices are real and the history is
continuous.
"""

from __future__ import annotations

import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field

from server.forecast.ninjatrader import ZONE_NAMES, Bar, Parsed
from server.forecast.sessions import trading_day
from server.ids import new_id
from server.models.forecast import ImportResult, SeriesInfo


@dataclass
class Series:
    symbol: str
    bars: list[Bar]
    contracts: list[str]
    rolls: list[str] = field(default_factory=list)


def save(conn: sqlite3.Connection, parsed: Parsed, filename: str) -> ImportResult:
    if not parsed.bars:
        raise ValueError("The file had no bars in it.")
    first, last = parsed.bars[0].t, parsed.bars[-1].t
    # One transaction: a year of bars is tens of thousands of rows, and autocommit per row is slow.
    with conn:
        conn.execute("BEGIN")
        conn.executemany(
            "INSERT OR REPLACE INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(parsed.symbol, parsed.contract, b.t, b.o, b.h, b.low, b.c, b.v) for b in parsed.bars],
        )
    conn.execute(
        "INSERT INTO candle_imports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            new_id("imp"),
            parsed.symbol,
            parsed.contract,
            filename,
            len(parsed.bars),
            first,
            last,
            parsed.zone,
            int(parsed.zone_assumed),
            parsed.source_minutes,
            int(time.time() * 1000),
        ),
    )
    return ImportResult(
        symbol=parsed.symbol,
        contract=parsed.contract,
        filename=filename,
        rows=parsed.rows,
        bars=len(parsed.bars),
        first=first,
        last=last,
        zone=ZONE_NAMES.get(parsed.zone, parsed.zone),
        zone_assumed=parsed.zone_assumed,
        source_minutes=parsed.source_minutes,
        stamps="bar end" if parsed.stamps_end else "bar start",
        notes=parsed.notes,
    )


def clear(conn: sqlite3.Connection, symbol: str) -> None:
    conn.execute("DELETE FROM candles WHERE symbol = ?", (symbol,))
    conn.execute("DELETE FROM candle_imports WHERE symbol = ?", (symbol,))


def _expiry(contract: str) -> tuple[int, int]:
    """ "03-25" -> (25, 3). A continuous file ("") sorts first: it is the oldest history."""
    if not contract:
        return (0, 0)
    month, year = contract.split("-")
    return (int(year), int(month))


def series(conn: sqlite3.Connection, symbol: str) -> Series:
    rows = conn.execute(
        "SELECT contract, t, open, high, low, close, volume FROM candles WHERE symbol = ? "
        "ORDER BY t",
        (symbol,),
    ).fetchall()
    by_contract: dict[str, list[Bar]] = defaultdict(list)
    for r in rows:
        by_contract[r["contract"]].append(
            Bar(r["t"], r["open"], r["high"], r["low"], r["close"], r["volume"])
        )
    order = sorted(by_contract, key=_expiry)
    if not order:
        return Series(symbol, [], [])
    return _stitch(symbol, order, by_contract)


def _daily_volume(bars: list[Bar]) -> dict[str, float]:
    days: dict[str, float] = defaultdict(float)
    for bar in bars:
        days[trading_day(bar.t)] += bar.v
    return days


def _stitch(symbol: str, order: list[str], by_contract: dict[str, list[Bar]]) -> Series:
    segments: list[list[Bar]] = []
    shifts: list[float] = []
    rolls: list[str] = []
    current = by_contract[order[0]]
    for name, nxt_name in zip(order, order[1:], strict=False):
        nxt = by_contract[nxt_name]
        cur_vol, nxt_vol = _daily_volume(current), _daily_volume(nxt)
        shared = sorted(set(cur_vol) & set(nxt_vol))
        day = next((d for d in shared if nxt_vol[d] > cur_vol[d]), None)
        roll_t = next((b.t for b in nxt if trading_day(b.t) == day), None) if day else None
        if roll_t is None:  # no overlap, or it never overtook: roll when the old one ends
            roll_t = next((b.t for b in nxt if b.t > current[-1].t), nxt[-1].t + 1)
        before = {b.t: b.c for b in current if b.t < roll_t}
        common = [b for b in nxt if b.t in before]
        shift = common[-1].c - before[common[-1].t] if common else 0.0
        segments.append([b for b in current if b.t < roll_t])
        shifts.append(shift)
        label = f"{name or 'history'} to {nxt_name}"
        rolls.append(
            f"{label} on {trading_day(roll_t)}, earlier prices shifted {shift:+g}"
            if common
            else f"{label}: no overlapping bars, so earlier prices were not adjusted"
        )
        current = [b for b in nxt if b.t >= roll_t]
    segments.append(current)
    shifts.append(0.0)
    bars: list[Bar] = []
    for i, segment in enumerate(segments):
        offset = sum(shifts[i:])
        bars.extend(
            Bar(b.t, b.o + offset, b.h + offset, b.low + offset, b.c + offset, b.v) for b in segment
        )
    return Series(symbol, bars, order, rolls)


def summary(conn: sqlite3.Connection) -> list[SeriesInfo]:
    out = []
    for row in conn.execute(
        "SELECT symbol, COUNT(DISTINCT t) AS bars, MIN(t) AS first, MAX(t) AS last, "
        "GROUP_CONCAT(DISTINCT contract) AS contracts FROM candles GROUP BY symbol ORDER BY symbol"
    ).fetchall():
        latest = conn.execute(
            "SELECT zone, zone_assumed FROM candle_imports WHERE symbol = ? "
            "ORDER BY imported_at DESC LIMIT 1",
            (row["symbol"],),
        ).fetchone()
        contracts = [c for c in (row["contracts"] or "").split(",") if c]
        out.append(
            SeriesInfo(
                symbol=row["symbol"],
                bars=row["bars"],
                first=row["first"],
                last=row["last"],
                contracts=sorted(contracts, key=_expiry),
                zone=ZONE_NAMES.get(latest["zone"], latest["zone"]) if latest else "",
                zone_assumed=bool(latest["zone_assumed"]) if latest else False,
            )
        )
    return out
