"""Your trade journal: NinjaTrader's trade export in, honest numbers out.

NinjaTrader 8 > Trade Performance > Trades, right-click > Export writes a CSV with one row per
round-trip trade. Net profit per trade is taken from the running "Cum. net profit" column when the
export has it (so commission is counted exactly once, whatever the Profit column includes), else
from Profit minus Commission. Importing the same export twice adds nothing.
"""

from __future__ import annotations

import csv
import io
import re
import sqlite3
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

from server.ids import new_id, now_ms
from server.models.trading import Breakdown, JournalImport, JournalStats, Trade

TIME_FORMATS = (
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M %p",
    "%Y-%m-%d %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
)
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def money(raw: str) -> float | None:
    """'$1,234.50' -> 1234.5, '($62.50)' and '-$62.50' -> -62.5. Empty -> None."""
    text = (raw or "").strip()
    if not text:
        return None
    negative = text.startswith("(") or text.startswith("-")
    digits = re.sub(r"[^\d.]", "", text)
    if not digits:
        return None
    value = float(digits)
    return -value if negative else value


def when(raw: str) -> datetime | None:
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _column(row: dict[str, str], *names: str) -> str:
    lowered = {k.strip().lower(): v or "" for k, v in row.items() if k}
    return next((lowered[n] for n in names if n in lowered), "")


HEAD = re.compile(r"^\(?-?\$?\d{1,3}$")
TAIL = re.compile(r"^\d{3}(\.\d+)?\)?$")


def _mend(fields: list[str], width: int) -> list[str]:
    """Rejoin "$1" + "234.50" into "$1,234.50" when an export left thousands commas unquoted -
    only when the row is too wide, and only where the pieces can only be one amount."""
    out: list[str] = []
    extra = len(fields) - width
    for field in fields:
        if extra > 0 and out and HEAD.match(out[-1]) and TAIL.match(field):
            out[-1] += "," + field
            extra -= 1
        else:
            out.append(field)
    return out


def _rows(text: str) -> list[dict[str, str]]:
    table = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not table:
        return []
    header = table[0]
    return [dict(zip(header, _mend(row, len(header)), strict=False)) for row in table[1:] if row]


def parse(text: str) -> tuple[list[Trade], int]:
    """The trades in an export, and how many rows could not be read."""
    trades: list[Trade] = []
    bad = 0
    previous_cum: float | None = None
    for row in _rows(text):
        entry, exit_ = when(_column(row, "entry time")), when(_column(row, "exit time"))
        entry_price = money(_column(row, "entry price"))
        exit_price = money(_column(row, "exit price"))
        qty = money(_column(row, "qty", "quantity"))
        position = _column(row, "market pos.", "market position", "side").strip().lower()
        if not (entry and exit_ and entry_price is not None and exit_price is not None and qty):
            bad += 1
            continue
        commission = money(_column(row, "commission")) or 0.0
        cum = money(_column(row, "cum. net profit", "cumulative net profit"))
        if cum is not None:
            net = cum - (previous_cum or 0.0)
            previous_cum = cum
        else:
            net = (money(_column(row, "profit")) or 0.0) - commission
        trades.append(
            Trade(
                id=new_id("trd"),
                account=_column(row, "account"),
                instrument=_column(row, "instrument").strip(),
                side="short" if position.startswith("short") or position == "sell" else "long",
                qty=abs(qty),
                entry_price=entry_price,
                exit_price=exit_price,
                entry_time=entry.strftime("%Y-%m-%d %H:%M:%S"),
                exit_time=exit_.strftime("%Y-%m-%d %H:%M:%S"),
                profit=round(net, 2),
                commission=commission,
                mae=money(_column(row, "mae")),
                mfe=money(_column(row, "mfe")),
                strategy=_column(row, "strategy"),
            )
        )
    return trades, bad


def save(conn: sqlite3.Connection, trades: list[Trade], bad: int) -> JournalImport:
    added = 0
    for t in trades:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO trades (id, account, instrument, side, qty, entry_price,"
            " exit_price, entry_time, exit_time, profit, commission, mae, mfe, strategy,"
            " imported_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                t.id,
                t.account,
                t.instrument,
                t.side,
                t.qty,
                t.entry_price,
                t.exit_price,
                t.entry_time,
                t.exit_time,
                t.profit,
                t.commission,
                t.mae,
                t.mfe,
                t.strategy,
                now_ms(),
            ),
        )
        added += cursor.rowcount
    return JournalImport(added=added, skipped=len(trades) - added, unreadable=bad)


def load(conn: sqlite3.Connection) -> list[Trade]:
    rows = conn.execute("SELECT * FROM trades ORDER BY entry_time").fetchall()
    return [Trade(**{k: v for k, v in dict(r).items() if k != "imported_at"}) for r in rows]


def _by(
    trades: list[Trade], key: Callable[[Trade], str], order: list[str] | None = None
) -> list[Breakdown]:
    groups: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        groups[key(t)].append(t)
    labels = [o for o in order if o in groups] if order else sorted(groups)
    return [
        Breakdown(
            label=label,
            trades=len(groups[label]),
            net=round(sum(t.profit for t in groups[label]), 2),
            win_rate=round(sum(t.profit > 0 for t in groups[label]) / len(groups[label]), 3),
        )
        for label in labels
    ]


def stats(trades: list[Trade]) -> JournalStats:
    if not trades:
        return JournalStats(
            trades=0,
            net=0,
            win_rate=0,
            avg_win=0,
            avg_loss=0,
            profit_factor=None,
            expectancy=0,
            max_drawdown=0,
        )
    wins = [t.profit for t in trades if t.profit > 0]
    losses = [t.profit for t in trades if t.profit <= 0]
    equity = peak = drawdown = 0.0
    for t in trades:
        equity += t.profit
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    entry = lambda t: datetime.strptime(t.entry_time, "%Y-%m-%d %H:%M:%S")  # noqa: E731
    return JournalStats(
        trades=len(trades),
        net=round(sum(t.profit for t in trades), 2),
        win_rate=round(len(wins) / len(trades), 3),
        avg_win=round(sum(wins) / len(wins), 2) if wins else 0.0,
        avg_loss=round(sum(losses) / len(losses), 2) if losses else 0.0,
        profit_factor=round(sum(wins) / -sum(losses), 2) if losses and sum(losses) < 0 else None,
        expectancy=round(sum(t.profit for t in trades) / len(trades), 2),
        max_drawdown=round(drawdown, 2),
        first=trades[0].entry_time,
        last=trades[-1].exit_time,
        by_weekday=_by(trades, lambda t: WEEKDAYS[entry(t).weekday()], WEEKDAYS),
        by_hour=_by(trades, lambda t: f"{entry(t).hour:02d}:00"),
        by_instrument=_by(trades, lambda t: t.instrument.split(" ")[0] or "?"),
        by_side=_by(trades, lambda t: t.side, ["long", "short"]),
    )
