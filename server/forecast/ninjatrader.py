"""Reading NinjaTrader exports into five-minute bars.

NinjaTrader 8's Historical Data > Export writes one bar per line, semicolon separated, no header:

    20241212 170100;6089.25;6090;6088.5;6089.5;123

Minute data exports as one-minute bars, so those are rolled up into five-minute bars here. A
comma separated file with a header row (Date, Time, Open, High, Low, Close, Volume - how charting
tools and spreadsheets save it) works too.

Two things an export does not say, and both matter:
- **The time zone.** It is whatever NinjaTrader was set to. Rather than ask, the daily CME halt
  gives it away: the last bar before the gap must end at 16:00 Chicago time. Each likely zone is
  tried and the one that puts the halt there wins.
- **Whether a time is a bar's start or its end.** NinjaTrader stamps the end; other tools stamp
  the start. The same halt tells them apart (16:00 versus 15:59 for one-minute bars).
Everything is stored in UTC by the bar's end, which is what NinjaTrader shows on a chart.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from server.forecast.sessions import BAR_S, CLOSE, EXCHANGE

CANDIDATE_ZONES = (
    "America/Chicago",
    "America/New_York",
    "UTC",
    "America/Los_Angeles",
    "America/Denver",
    "Europe/London",
    "Europe/Berlin",
)
ZONE_NAMES = {
    "America/Chicago": "US Central",
    "America/New_York": "US Eastern",
    "UTC": "UTC",
    "America/Los_Angeles": "US Pacific",
    "America/Denver": "US Mountain",
    "Europe/London": "UK",
    "Europe/Berlin": "Central Europe",
}
SYMBOL = re.compile(r"\b(MES|MNQ|ES|NQ)\b[ _]*(?:(\d{2})[-_ ]?(\d{2}))?", re.I)
DATE_FORMATS = (
    "%Y%m%d %H%M%S",
    "%Y%m%d %H%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M %p",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
)
MAX_SOURCE_MINUTES = 5


class ImportFailed(ValueError):
    """Said to the person importing, so it names the file's problem in plain words."""


@dataclass
class Bar:
    t: int
    """UTC epoch seconds at which the bar ends."""
    o: float
    h: float
    low: float
    c: float
    v: float


@dataclass
class Parsed:
    symbol: str
    contract: str
    bars: list[Bar]
    zone: str
    zone_assumed: bool
    stamps_end: bool
    source_minutes: int
    rows: int
    notes: list[str] = field(default_factory=list)


def symbol_from_name(filename: str) -> tuple[str, str]:
    """`ES 03-25.Last.txt` -> ("ES", "03-25"). No month in the name means a continuous series."""
    match = SYMBOL.search(filename)
    if not match:
        return "", ""
    month, year = match.group(2), match.group(3)
    return match.group(1).upper(), f"{month}-{year}" if month and year else ""


def _rows(text: str) -> tuple[list[datetime], list[tuple[float, ...]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ImportFailed("The file is empty.")
    delimiter = ";" if lines[0].count(";") >= 4 else "\t" if "\t" in lines[0] else ","
    header = not any(ch.isdigit() for ch in lines[0].split(delimiter)[0][:4])
    fmt: str | None = None
    times: list[datetime] = []
    values: list[tuple[float, ...]] = []
    for number, line in enumerate(lines[1:] if header else lines, start=2 if header else 1):
        cells = [c.strip().strip('"') for c in line.split(delimiter)]
        # "Date;Time;..." exports split the timestamp over two cells.
        split_time = len(cells) >= 7 or (len(cells) == 6 and ":" in cells[1])
        stamp = f"{cells[0]} {cells[1]}" if split_time else cells[0]
        numbers = cells[2:] if split_time else cells[1:]
        if len(numbers) < 4:
            raise ImportFailed(
                f"Line {number} has {len(numbers)} numbers; a bar needs at least four."
            )
        fmt = fmt or _format_of(stamp)
        try:
            times.append(datetime.strptime(stamp, fmt))
            values.append(tuple(float(n) for n in (numbers + ["0"])[:5]))
        except ValueError as exc:
            raise ImportFailed(f"Line {number} could not be read: {line[:60]!r}") from exc
    return times, values


def _format_of(stamp: str) -> str:
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(stamp, fmt)
            return fmt
        except ValueError:
            continue
    raise ImportFailed(
        f"Couldn't read the date {stamp!r}. Export from NinjaTrader 8, or use yyyy-mm-dd hh:mm."
    )


def _detect(times: list[datetime], bar_minutes: int) -> tuple[str, bool, bool]:
    """(zone, stamps are bar ends, assumed) - from where the daily halt lands."""
    halts = [
        times[i - 1]
        for i in range(1, len(times))
        if timedelta(minutes=40) <= times[i] - times[i - 1] <= timedelta(hours=3)
    ]
    best, best_score = ("America/Chicago", True), 0
    for zone in CANDIDATE_ZONES:
        tz = ZoneInfo(zone)
        local = Counter(
            (t.replace(tzinfo=tz).astimezone(EXCHANGE)).hour * 60
            + (t.replace(tzinfo=tz).astimezone(EXCHANGE)).minute
            for t in halts
        )
        for stamps_end, minute in ((True, CLOSE), (False, CLOSE - bar_minutes)):
            if local[minute] > best_score:
                best, best_score = (zone, stamps_end), local[minute]
    return best[0], best[1], best_score == 0


def parse(text: str, filename: str, symbol_hint: str = "") -> Parsed:
    symbol, contract = symbol_from_name(filename)
    symbol = symbol or symbol_hint.upper()
    if not symbol:
        raise ImportFailed("Couldn't tell which market this is. Name the file like ES 03-25.txt.")
    times, values = _rows(text)
    order = sorted(range(len(times)), key=times.__getitem__)
    times, values = [times[i] for i in order], [values[i] for i in order]
    deltas = Counter((b - a).total_seconds() // 60 for a, b in zip(times, times[1:], strict=False))
    minutes = int(deltas.most_common(1)[0][0]) if deltas else 5
    if minutes < 1 or minutes > MAX_SOURCE_MINUTES or BAR_S // 60 % minutes:
        raise ImportFailed(
            f"These are {minutes}-minute bars. Export 1-minute or 5-minute data "
            "(NinjaTrader: Tools > Historical Data > Export, Data type Last, Minute)."
        )
    zone, stamps_end, assumed = _detect(times, minutes)
    bars = _roll_up(times, values, ZoneInfo(zone), minutes, stamps_end)
    notes = []
    if assumed:
        notes.append(
            "The file had no daily halt to read its time zone from, so US Central was assumed."
        )
    return Parsed(symbol, contract, bars, zone, assumed, stamps_end, minutes, len(times), notes)


def _roll_up(
    times: list[datetime],
    values: list[tuple[float, ...]],
    tz: ZoneInfo,
    minutes: int,
    stamps_end: bool,
) -> list[Bar]:
    shift = 0 if stamps_end else minutes * 60
    buckets: dict[int, Bar] = {}
    for when, (o, h, low, c, v) in zip(times, values, strict=True):
        end = int(when.replace(tzinfo=tz).timestamp()) + shift
        key = -(-end // BAR_S) * BAR_S  # the five-minute bar this minute closes inside
        bar = buckets.get(key)
        if bar is None:
            buckets[key] = Bar(key, o, h, low, c, v)
        else:
            bar.h, bar.low, bar.c, bar.v = max(bar.h, h), min(bar.low, low), c, bar.v + v
    return [buckets[k] for k in sorted(buckets)]
