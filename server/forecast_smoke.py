"""`JARVIS_SMOKE_FORECAST=1` for the packaged app: fetch the real Kronos weights the way the
Forecast sheet's button does, import a NinjaTrader-format export, forecast it, and check the
answer has the shape it should. Proves PyTorch and the tokenizer survived PyInstaller.

The export is a seeded random walk on the CME calendar - a test fixture, so it lives here with
the smoke test and never in anything a person could mistake for market data.
"""

from __future__ import annotations

import json
import random
import time
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from server.forecast.sessions import EXCHANGE, is_trading

WAIT_S = 600.0


def sample_export(days: int = 5) -> bytes:
    rng, price, lines = random.Random(7), 6000.0, []
    end = datetime(2024, 12, 9, 16, 0, tzinfo=EXCHANGE)
    stop = end + timedelta(days=days)
    while end < stop:
        end += timedelta(minutes=1)
        if not is_trading(end - timedelta(minutes=1)):
            continue
        o = price
        price += rng.choice((-0.25, 0.0, 0.25)) * rng.randint(1, 4)
        h, low = max(o, price) + 0.25, min(o, price) - 0.25
        lines.append(f"{end:%Y%m%d %H%M%S};{o};{h};{low};{price};{rng.randint(50, 500)}")
    return "\n".join(lines).encode()


def _wait(url: str, get: Callable[[str], Any], busy: tuple[str, ...]) -> dict[str, Any]:
    deadline = time.monotonic() + WAIT_S
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = get(url) or {}
        if state.get("state") not in busy:
            break
        time.sleep(2)
    return state


def forecast(url: str, request: Callable[..., bytes], get: Callable[[str], Any]) -> tuple[str, str]:
    """(the forecast's summary, why not)."""
    try:
        request(f"{url}/api/forecast/pack", b"", timeout=30)
        pack = _wait(f"{url}/api/forecast/pack", get, ("downloading", "verifying"))
        if pack.get("state") != "done":
            return "", f"Kronos download did not finish: {pack}"
        name = urllib.parse.quote("ES 03-25.Last.txt")
        request(f"{url}/api/forecast/import?filename={name}", sample_export(), timeout=60)
        request(f"{url}/api/forecast/run", {"symbol": "ES", "horizon": 12}, timeout=30)
    except OSError as exc:
        return "", f"forecast request failed: {exc}"
    job = _wait(f"{url}/api/forecast/job", get, ("loading", "running"))
    result = job.get("forecast") or {}
    if job.get("state") != "done" or len(result.get("steps", [])) != 12:
        return "", f"forecast did not finish: {json.dumps(job)[:600]}"
    return str(result.get("summary", "")), ""
