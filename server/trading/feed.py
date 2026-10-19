"""Live bars from NinjaTrader, by way of a text file.

The JarvisFeed indicator (ninjascript/JarvisFeed.cs) appends one line per finished five-minute bar
to `<NinjaTrader 8>/jarvis/<instrument>.jarvis.txt`:

    1760880900;5812.25;5813.5;5811;5813;1834

bar end in UTC epoch seconds, then OHLCV. A file instead of a socket: nothing listens on a port,
NinjaTrader needs no permission to talk to anything, and if Jarvis is closed the bars wait in the
file until it opens. Each file is read from where it was last left, whole lines only.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from server.forecast.ninjatrader import Bar, symbol_from_name
from server.forecast.sessions import exchange_time, is_trading

log = logging.getLogger("jarvis.trading")
SUFFIX = ".jarvis.txt"
STALE_S = 15 * 60


def default_dir() -> Path:
    return Path.home() / "Documents" / "NinjaTrader 8" / "jarvis"


def parse_lines(text: str) -> list[Bar]:
    bars: list[Bar] = []
    for line in text.splitlines():
        parts = line.strip().split(";")
        if len(parts) != 6:
            continue
        try:
            t, o, h, low, c, v = int(parts[0]), *(float(p) for p in parts[1:])
        except ValueError:
            continue
        bars.append(Bar(t, o, h, low, c, v))
    return bars


@dataclass
class Latest:
    symbol: str
    contract: str
    t: int
    close: float
    bars: int = 0
    """Bars received from the live file since Jarvis started."""


@dataclass
class Feed:
    folder: Path
    offsets: dict[str, int] = field(default_factory=dict)
    latest: dict[str, Latest] = field(default_factory=dict)

    def files(self) -> list[Path]:
        if not self.folder.is_dir():
            return []
        return sorted(p for p in self.folder.iterdir() if p.name.endswith(SUFFIX))

    def poll(self, conn: sqlite3.Connection) -> dict[str, list[Bar]]:
        """Read what is new in every feed file and store it. Returns the new bars by symbol."""
        found: dict[str, list[Bar]] = {}
        for path in self.files():
            symbol, contract = symbol_from_name(path.name)
            if not symbol:
                continue
            key = str(path)
            size = path.stat().st_size
            start = self.offsets.get(key, 0)
            if size < start:  # the file was replaced: read it again from the top
                start = 0
            if size == start:
                continue
            with path.open("rb") as handle:
                handle.seek(start)
                chunk = handle.read(size - start).decode("utf-8", "replace")
            complete = chunk.rsplit("\n", 1)[0] if "\n" in chunk else ""
            self.offsets[key] = start + len(complete.encode()) + (1 if complete else 0)
            bars = parse_lines(complete)
            if not bars:
                continue
            with conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(symbol, contract, b.t, b.o, b.h, b.low, b.c, b.v) for b in bars],
                )
            last = bars[-1]
            known = self.latest.get(symbol)
            if known is None or last.t >= known.t:
                count = (known.bars if known else 0) + len(bars)
                self.latest[symbol] = Latest(symbol, contract, last.t, last.c, count)
            found.setdefault(symbol, []).extend(bars)
        return found

    def stale(self, symbol: str, now: float | None = None) -> bool:
        """No bar for a while, while the market is open: the chart was closed or the feed broke."""
        known = self.latest.get(symbol)
        now = time.time() if now is None else now
        if known is None:
            return False
        return now - known.t > STALE_S and is_trading(exchange_time(int(now)))
