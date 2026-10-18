"""Futures forecasting: the calendar, reading NinjaTrader exports, rolling contracts, and a full
forecast and backtest through a tiny untrained Kronos (the real weights are fetched in-app; CI's
packaged-app smoke test runs those)."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from server.db.connection import Database
from server.db.migrate import migrate
from server.forecast import ninjatrader, runs, store
from server.forecast.sessions import EXCHANGE, exchange_time, next_bar_ends
from server.settings import load_settings

CT = EXCHANGE
ET = ZoneInfo("America/New_York")


def ts(zone: ZoneInfo, *args: int) -> int:
    return int(datetime(*args, tzinfo=zone).timestamp())


def globex_minutes(start: datetime, days: int) -> list[datetime]:
    """One-minute bar end times in Chicago time across `days` sessions, halts and weekends out."""
    out, t = [], start
    while t < start + timedelta(days=days):
        t += timedelta(minutes=1)
        if ninjatrader_open(t - timedelta(minutes=1)):
            out.append(t)
    return out


def ninjatrader_open(minute_start: datetime) -> bool:
    from server.forecast.sessions import is_trading

    return is_trading(minute_start)


def nt_export(zone: ZoneInfo, days: int = 4, seed: int = 1, start_price: float = 6000.0) -> str:
    rng, price, lines = random.Random(seed), start_price, []
    for end in globex_minutes(datetime(2024, 12, 9, 16, 0, tzinfo=CT), days):
        o = price
        price += rng.choice((-0.25, 0, 0.25)) * rng.randint(1, 4)
        h, low = max(o, price) + 0.25, min(o, price) - 0.25
        local = end.astimezone(zone).strftime("%Y%m%d %H%M%S")
        lines.append(f"{local};{o};{h};{low};{price};{rng.randint(50, 500)}")
    return "\n".join(lines)


def test_calendar_skips_the_daily_halt_and_the_weekend() -> None:
    thursday = ts(CT, 2024, 12, 12, 15, 55)
    after = next_bar_ends(thursday, 2)
    assert [exchange_time(t).strftime("%a %H:%M") for t in after] == ["Thu 16:00", "Thu 17:05"]
    friday_close = ts(CT, 2024, 12, 13, 16, 0)
    assert exchange_time(next_bar_ends(friday_close, 1)[0]).strftime("%a %H:%M") == "Sun 17:05"


def test_ninjatrader_minutes_in_eastern_time_become_five_minute_bars() -> None:
    parsed = ninjatrader.parse(nt_export(ET), "ES 03-25.Last.txt")
    assert (parsed.symbol, parsed.contract) == ("ES", "03-25")
    assert parsed.zone == "America/New_York" and not parsed.zone_assumed
    assert parsed.stamps_end and parsed.source_minutes == 1
    assert {(b.t % 300) for b in parsed.bars} == {0}
    # The bar ending Thursday 16:00 Chicago exists; nothing ends inside the halt.
    ends = {exchange_time(b.t).strftime("%a %H:%M") for b in parsed.bars}
    assert "Thu 16:00" in ends and "Thu 16:30" not in ends and "Thu 17:05" in ends
    first_five = parsed.rows and parsed.bars[0]
    assert first_five and first_five.h >= max(first_five.o, first_five.c)


def test_header_csv_stamped_by_bar_start_in_utc() -> None:
    rows = ["Date,Time,Open,High,Low,Close,Volume"]
    for end in (
        e for e in globex_minutes(datetime(2024, 12, 9, 16, 0, tzinfo=CT), 3) if e.minute % 5 == 0
    ):
        start = (end - timedelta(minutes=5)).astimezone(ZoneInfo("UTC"))
        rows.append(f"{start:%Y-%m-%d},{start:%H:%M},1,2,0.5,1.5,10")
    parsed = ninjatrader.parse("\n".join(rows), "export.csv", symbol_hint="nq")
    assert parsed.symbol == "NQ" and parsed.zone == "UTC" and not parsed.stamps_end


def test_wrong_timeframe_is_refused_in_words() -> None:
    hourly = "\n".join(
        f"2024121{d} {h:02d}0000;1;2;0.5;1.5;10" for d in range(2, 6) for h in range(24)
    )
    with pytest.raises(ninjatrader.ImportFailed, match="60-minute"):
        ninjatrader.parse(hourly, "ES 03-25.txt")


@pytest.fixture
def conn(tmp_path: Path):  # type: ignore[no-untyped-def]
    db = Database(tmp_path / "t.db")
    with db.session() as c:
        migrate(c)
        yield c


def test_contracts_roll_on_volume_and_history_is_back_adjusted(conn) -> None:  # type: ignore[no-untyped-def]
    old = ninjatrader.parse(nt_export(CT, seed=2), "ES 12-24.Last.txt")
    new = ninjatrader.parse(nt_export(CT, seed=2, start_price=6010.0), "ES 03-25.Last.txt")
    # The new contract trades more from the third session on.
    third = sorted({store.trading_day(b.t) for b in new.bars})[2]
    for bar in new.bars:
        bar.v *= 10 if store.trading_day(bar.t) >= third else 0.1
    store.save(conn, old, "ES 12-24.Last.txt")
    store.save(conn, new, "ES 03-25.Last.txt")
    series = store.series(conn, "ES")
    assert series.contracts == ["12-24", "03-25"]
    assert "shifted +10" in series.rolls[0]
    # Same random walk 10 points apart: after adjusting, the seam is invisible.
    by_t = {b.t: b.c for b in series.bars}
    assert all(abs(by_t[b.t] - b.c) < 1e-9 for b in new.bars if b.t in by_t)
    assert [i.symbol for i in store.summary(conn)] == ["ES"]


def tiny_kronos(models_dir: Path) -> None:
    from server.forecast.kronos import Kronos, KronosTokenizer

    KronosTokenizer(
        d_in=6, d_model=16, n_heads=2, ff_dim=32, n_enc_layers=1, n_dec_layers=1,
        ffn_dropout_p=0, attn_dropout_p=0, resid_dropout_p=0, s1_bits=4, s2_bits=4,
        beta=0.05, gamma0=1.0, gamma=1.1, zeta=0.05, group_size=4,
    ).save_pretrained(models_dir / "kronos" / "Kronos-Tokenizer-base")  # fmt: skip
    Kronos(
        s1_bits=4, s2_bits=4, n_layers=1, d_model=16, n_heads=2, ff_dim=32, ffn_dropout_p=0,
        attn_dropout_p=0, resid_dropout_p=0, token_dropout_p=0, learn_te=True,
    ).save_pretrained(models_dir / "kronos" / "Kronos-small")  # fmt: skip


def test_forecast_and_backtest_end_to_end(tmp_path: Path, conn) -> None:  # type: ignore[no-untyped-def]
    pytest.importorskip("torch")
    from server.forecast.engine import Engine

    tiny_kronos(tmp_path)
    settings = load_settings(
        paths={"models_dir": tmp_path}, forecast={"lookback": 128, "paths": 4, "backtest_paths": 2}
    )
    engine = Engine(settings)
    assert engine.status().weights and engine.status().runtime
    store.save(conn, ninjatrader.parse(nt_export(CT), "NQ 03-25.txt"), "NQ 03-25.txt")
    series = store.series(conn, "NQ")
    steps: list[int] = []

    result = runs.forecast(engine, series, 6, lambda step, total: steps.append(step))
    assert steps == [1, 2, 3, 4, 5, 6]
    assert len(result.steps) == 6 and len(result.paths) == 4
    assert all(
        s.l <= min(s.o, s.c) and s.h >= max(s.o, s.c) and s.p10 <= s.p90 for s in result.steps
    )
    assert result.steps[0].t > series.bars[-1].t and 0 <= result.prob_up <= 1
    assert (result.tick_size, result.tick_value) == (0.25, 5.0)
    assert (
        result.summary.startswith("NQ 5-minute Kronos forecast")
        and "30 min ahead" in result.summary
    )

    scored = runs.backtest(engine, series, 6, 4, lambda *_: None)
    assert scored.windows == 4 and 0 <= scored.coverage <= 1
    assert scored.mae_naive > 0


def test_the_packaged_smoke_tests_export_reads_as_chicago() -> None:
    from server.forecast_smoke import sample_export

    parsed = ninjatrader.parse(sample_export().decode(), "ES 03-25.Last.txt")
    assert parsed.zone == "America/Chicago" and not parsed.zone_assumed and len(parsed.bars) > 1000
