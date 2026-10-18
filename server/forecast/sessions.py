"""When CME equity index futures (ES, NQ and their micros) trade, in exchange time.

Globex runs Sunday 17:00 to Friday 16:00 Chicago time, with a one-hour halt from 16:00 to 17:00
Monday to Thursday. A forecast must only ask for bars that will exist: one step past Thursday
15:55 is Thursday 16:00, and the next one is 17:05, not 16:05.

Holidays and early closes are not in here yet. A forecast that runs into one shows bars for a
session that will not happen, and the sheet says so.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

EXCHANGE = ZoneInfo("America/Chicago")
BAR_S = 300
OPEN, CLOSE = 17 * 60, 16 * 60  # minutes after midnight, exchange time
FRIDAY, SATURDAY, SUNDAY = 4, 5, 6


def exchange_time(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, UTC).astimezone(EXCHANGE)


def is_trading(minute_start: datetime) -> bool:
    """Is Globex open for the minute that starts at this exchange-time instant?"""
    day, minute = minute_start.weekday(), minute_start.hour * 60 + minute_start.minute
    if day == SATURDAY:
        return False
    if day == SUNDAY:
        return minute >= OPEN
    if day == FRIDAY:
        return minute < CLOSE
    return minute < CLOSE or minute >= OPEN


def bar_exists(end_ts: int, bar_s: int = BAR_S) -> bool:
    """A bar is labelled by when it ends (NinjaTrader's convention, and ours once imported). It
    exists when the market is open at the start of its first minute."""
    return is_trading(exchange_time(end_ts - bar_s))


def next_bar_ends(last_end_ts: int, count: int, bar_s: int = BAR_S) -> list[int]:
    """The `count` bar end times that follow `last_end_ts`, skipping halts and weekends."""
    out: list[int] = []
    ts = last_end_ts
    # A weekend is about 600 five-minute bars long; no real gap is anywhere near this bound.
    for _ in range(count + 5000):
        if len(out) == count:
            break
        ts += bar_s
        if bar_exists(ts, bar_s):
            out.append(ts)
    return out


def trading_day(end_ts: int) -> str:
    """The session a bar belongs to, named by the date it ends on: Sunday evening's bars are
    Monday's session, as the exchange counts it."""
    local = exchange_time(end_ts - 1)
    if local.hour * 60 + local.minute >= OPEN:
        local += timedelta(days=1)
    return local.date().isoformat()
