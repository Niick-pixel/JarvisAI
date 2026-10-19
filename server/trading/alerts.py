"""Alert rules, and checking them as bars and forecasts arrive.

Each rule fires once when its condition becomes true, then stays quiet until the condition has
stopped being true (it "re-arms"). Price sitting on a level, or a forecast hovering at 70% up,
must not ring every five minutes.
"""

from __future__ import annotations

import sqlite3

from server.db import repo
from server.forecast.ninjatrader import Bar
from server.ids import new_id, now_ms
from server.models.trading import AlertEvent, AlertRule, AlertRuleCreate

RANGE_BARS = 12
"""`range` looks at the last hour of five-minute bars."""


def rules(conn: sqlite3.Connection) -> list[AlertRule]:
    rows = conn.execute("SELECT * FROM alert_rules ORDER BY created_at").fetchall()
    return [
        AlertRule(**{**dict(r), "enabled": bool(r["enabled"]), "armed": bool(r["armed"])})
        for r in rows
    ]


def add(conn: sqlite3.Connection, body: AlertRuleCreate) -> AlertRule:
    rule = AlertRule(**body.model_dump(), id=new_id("alr"), created_at=now_ms())
    rule.symbol = rule.symbol.upper()
    conn.execute(
        "INSERT INTO alert_rules (id, symbol, kind, value, enabled, armed, created_at)"
        " VALUES (?,?,?,?,1,1,?)",
        (rule.id, rule.symbol, rule.kind, rule.value, rule.created_at),
    )
    return rule


def remove(conn: sqlite3.Connection, rule_id: str) -> None:
    conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))


def events(conn: sqlite3.Connection, limit: int = 20) -> list[AlertEvent]:
    rows = conn.execute(
        "SELECT * FROM alert_events ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [AlertEvent(**dict(r)) for r in rows]


def mark_read(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE alert_events SET read_at = ? WHERE read_at IS NULL", (now_ms(),))


def _condition(
    rule: AlertRule, bars: list[Bar], prob_up: float | None, stale: bool
) -> tuple[bool, str] | None:
    """(is it true now, what to say if it fires). None when there is nothing to judge it on."""
    last = bars[-1] if bars else None
    if rule.kind == "stale":
        return stale, f"{rule.symbol}: no new bar from NinjaTrader for over 15 minutes"
    if rule.kind in ("above", "below"):
        if last is None:
            return None
        hit = last.c > rule.value if rule.kind == "above" else last.c < rule.value
        return hit, f"{rule.symbol} closed {rule.kind} {rule.value:g} at {last.c:g}"
    if rule.kind in ("prob_up", "prob_down"):
        if prob_up is None:
            return None
        share = prob_up * 100 if rule.kind == "prob_up" else (1 - prob_up) * 100
        way = "higher" if rule.kind == "prob_up" else "lower"
        return share >= rule.value, (
            f"{rule.symbol}: {share:.0f}% of forecast paths end {way} in the next hour"
        )
    window = bars[-RANGE_BARS:]
    if len(window) < 2:
        return None
    span = max(b.h for b in window) - min(b.low for b in window)
    return span >= rule.value, f"{rule.symbol}: {span:g} point range in the last hour"


def check(
    conn: sqlite3.Connection,
    symbol: str,
    bars: list[Bar],
    *,
    prob_up: float | None = None,
    stale: bool = False,
) -> list[AlertEvent]:
    """Judge every rule for this symbol against the latest bars. Returns what fired."""
    fired: list[AlertEvent] = []
    for rule in rules(conn):
        if rule.symbol != symbol or not rule.enabled:
            continue
        verdict = _condition(rule, bars, prob_up, stale)
        if verdict is None:
            continue
        hit, message = verdict
        if hit and rule.armed:
            event = AlertEvent(
                id=new_id("alv"),
                rule_id=rule.id,
                symbol=symbol,
                message=message,
                created_at=now_ms(),
            )
            conn.execute(
                "INSERT INTO alert_events (id, rule_id, symbol, message, created_at)"
                " VALUES (?,?,?,?,?)",
                (event.id, rule.id, symbol, message, event.created_at),
            )
            repo.agents.add_inbox(
                conn, job_run_id=None, title=f"Alert: {symbol}", body=message, flags=[]
            )
            fired.append(event)
        if hit == rule.armed:  # fired: disarm. Condition gone while disarmed: re-arm.
            conn.execute("UPDATE alert_rules SET armed = ? WHERE id = ?", (int(not hit), rule.id))
    return fired
