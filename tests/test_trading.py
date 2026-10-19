"""The trading co-pilot: live bars from the JarvisFeed file, alerts that ring once, and a trade
journal read from NinjaTrader's own export."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from conftest import FakeProvider
from fastapi.testclient import TestClient

from server.db.connection import Database
from server.forecast.ninjatrader import Bar
from server.main import create_app
from server.models.trading import AlertRuleCreate
from server.providers.base import StreamItem
from server.providers.registry import ProviderRegistry
from server.settings import Settings
from server.trading import alerts, journal
from server.trading.feed import Feed

T0 = 1_760_880_000  # a bar end, UTC


def line(t: int, close: float) -> str:
    return f"{t};{close - 1};{close + 1};{close - 2};{close};100\n"


def test_the_feed_reads_whole_lines_once_and_survives_a_replaced_file(
    db: Database, tmp_path: Path
) -> None:
    folder = tmp_path / "feed"
    folder.mkdir()
    file = folder / "ES 12-26.jarvis.txt"
    file.write_text(
        line(T0, 5800) + line(T0 + 300, 5801) + "1760880600;58"
    )  # last line half-written
    feed = Feed(folder)
    with db.session() as conn:
        assert [b.c for b in feed.poll(conn)["ES"]] == [5800, 5801]
        assert feed.poll(conn) == {}  # nothing new, nothing read twice
        with file.open("a") as handle:
            handle.write("02;5803;5797;5802;90\n")  # the half line, finished
        assert [b.c for b in feed.poll(conn)["ES"]] == [5802]
        file.write_text(line(T0 + 900, 5805))  # replaced by a shorter file
        assert [b.c for b in feed.poll(conn)["ES"]] == [5805]
        stored = conn.execute("SELECT COUNT(*) FROM candles WHERE contract = '12-26'").fetchone()[0]
    assert stored == 4
    assert feed.latest["ES"].close == 5805 and feed.latest["ES"].contract == "12-26"


def test_an_alert_rings_once_then_rearms(db: Database) -> None:
    bar = lambda c: Bar(T0, c, c + 1, c - 1, c, 1)  # noqa: E731
    with db.session() as conn:
        alerts.add(conn, AlertRuleCreate(symbol="es", kind="above", value=5850))
        assert alerts.check(conn, "ES", [bar(5840)]) == []
        [fired] = alerts.check(conn, "ES", [bar(5851)])
        assert fired.message == "ES closed above 5850 at 5851"
        assert alerts.check(conn, "ES", [bar(5855)]) == []  # still above: quiet
        assert alerts.check(conn, "ES", [bar(5849)]) == []  # back below: re-armed
        assert len(alerts.check(conn, "ES", [bar(5852)])) == 1  # crosses again: rings again
        inbox = conn.execute("SELECT COUNT(*) FROM inbox").fetchone()[0]
    assert inbox == 2


def test_forecast_range_and_stale_alerts(db: Database) -> None:
    with db.session() as conn:
        alerts.add(conn, AlertRuleCreate(symbol="NQ", kind="prob_down", value=70))
        alerts.add(conn, AlertRuleCreate(symbol="NQ", kind="range", value=40))
        alerts.add(conn, AlertRuleCreate(symbol="NQ", kind="stale", value=15))
        bars = [Bar(T0 + i * 300, 100, 100 + i * 10, 100, 100, 1) for i in range(6)]
        fired = alerts.check(conn, "NQ", bars, prob_up=0.2, stale=True)
    assert sorted(e.message for e in fired) == [
        "NQ: 50 point range in the last hour",
        "NQ: 80% of forecast paths end lower in the next hour",
        "NQ: no new bar from NinjaTrader for over 15 minutes",
    ]


def test_live_status_shows_the_feed_and_what_fired(settings: Settings) -> None:
    folder = Path(settings.trading.feed_dir)
    folder.mkdir(parents=True)
    (folder / "NQ 12-26.jarvis.txt").write_text(line(T0, 21000) + line(T0 + 300, 21100))
    app = create_app(settings)
    with TestClient(app) as client:
        asyncio.run(app.state.app.copilot.tick())
        # Added after the bars arrived, and already true: it says so straight away.
        client.post("/api/trading/alerts", json={"symbol": "NQ", "kind": "above", "value": 21050})
        live = client.get("/api/trading/live").json()
        [nq] = live["symbols"]
        assert (nq["symbol"], nq["last_close"], nq["bars_received"]) == ("NQ", 21100, 2)
        assert live["events"][0]["message"] == "NQ closed above 21050 at 21100"
        assert client.get("/api/trading/ninjascript").text.startswith("// JarvisFeed")


EXPORT = """﻿Trade number,Instrument,Account,Strategy,Market pos.,Qty,Entry price,Exit price,Entry time,Exit time,Entry name,Exit name,Profit,Cum. net profit,Commission,MAE,MFE,ETD,Bars
1,ES 12-26,Sim101,,Long,1,5800.00,5804.00,10/13/2026 9:35:00 AM,10/13/2026 9:50:00 AM,Buy,Sell,$200.00,$195.70,$4.30,$25.00,$237.50,$37.50,3
2,ES 12-26,Sim101,,Short,2,5810.00,5812.00,10/14/2026 10:05:00 AM,10/14/2026 10:20:00 AM,Sell,Buy,($200.00),($12.90),$8.60,$300.00,$50.00,$250.00,3
3,NQ 12-26,Sim101,,Long,1,21000.00,21010.00,10/14/2026 2:10:00 PM,10/14/2026 2:30:00 PM,Buy,Sell,$200.00,$182.80,$4.30,$40.00,$260.00,$60.00,4
bad row
"""  # noqa: E501 - an export's rows are as long as they are


class Coach(FakeProvider):
    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        self.shown = messages[-1].content
        self.script = ["Your one loser was a short on Tuesday."]
        async for item in super().stream(messages, params, **kwargs):
            yield item


def test_the_journal_reads_ninjatraders_export_and_answers_from_it(settings: Settings) -> None:
    trades, bad = journal.parse(EXPORT)
    # Net from the running total, so commission is counted once whatever "Profit" includes.
    assert [t.profit for t in trades] == [195.7, -208.6, 195.7]
    assert [t.side for t in trades] == ["long", "short", "long"]
    assert trades[0].entry_time == "2026-10-13 09:35:00" and bad == 1

    coach = Coach()
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([coach])
    with TestClient(app) as client:
        first = client.post("/api/trading/journal/import", content=EXPORT.encode()).json()
        again = client.post("/api/trading/journal/import", content=EXPORT.encode()).json()
        assert (first["added"], first["unreadable"]) == (3, 1)
        assert (again["added"], again["skipped"]) == (0, 3)

        stats = client.get("/api/trading/journal").json()
        assert (stats["trades"], stats["net"], stats["win_rate"]) == (3, 182.8, 0.667)
        assert stats["max_drawdown"] == 208.6
        assert [(b["label"], b["trades"]) for b in stats["by_weekday"]] == [
            ("Tuesday", 1),
            ("Wednesday", 2),
        ]

        answer = client.post(
            "/api/trading/journal/ask", json={"question": "Where do I lose?"}
        ).json()
        assert answer["answer"] == "Your one loser was a short on Tuesday."
        assert '<context source="journal:trades">' in coach.shown
        assert "2026-10-14 10:05:00,2026-10-14 10:20:00,ES 12-26,short,2" in coach.shown


def test_unquoted_thousands_in_an_export_are_mended() -> None:
    export = (
        "Instrument,Market pos.,Qty,Entry price,Exit price,Entry time,Exit time,Profit,"
        "Cum. net profit,Commission\n"
        "ES 12-26,Long,2,5800,5812,10/13/2026 9:35:00 AM,10/13/2026 9:50:00 AM,$1,200.00,"
        "$1,191.40,$8.60\n"
        "ES 12-26,Short,1,5812,5820,10/13/2026 10:35:00 AM,10/13/2026 10:50:00 AM,($400.00),"
        "$787.10,$4.30\n"
    )
    trades, bad = journal.parse(export)
    assert bad == 0
    assert [t.profit for t in trades] == [1191.4, -404.3]
