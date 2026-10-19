"""The trading co-pilot: live feed state, alert rules and what they said, and the trade journal."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AlertKind = Literal["above", "below", "prob_up", "prob_down", "range", "stale"]


class AlertRuleCreate(BaseModel):
    symbol: str
    kind: AlertKind
    value: float
    """A price for above/below; a percent for prob_up/prob_down; points for range; minutes for
    stale."""


class AlertRule(AlertRuleCreate):
    id: str
    enabled: bool = True
    armed: bool = True
    created_at: int


class AlertEvent(BaseModel):
    id: str
    rule_id: str | None = None
    symbol: str
    message: str
    created_at: int
    read_at: int | None = None


class LiveSymbol(BaseModel):
    symbol: str
    contract: str
    last_t: int
    last_close: float
    bars_received: int
    stale: bool
    forecast: str = ""
    """The latest rolling forecast in words, empty until one has run."""
    prob_up: float | None = None
    forecast_at: int | None = None


class LiveStatus(BaseModel):
    folder: str
    folder_exists: bool
    files: list[str]
    symbols: list[LiveSymbol]
    forecasting: bool
    """Whether rolling forecasts can run - the model and its runtime are installed."""
    events: list[AlertEvent]
    """Recent alerts, newest first."""


class Trade(BaseModel):
    id: str
    account: str
    instrument: str
    side: Literal["long", "short"]
    qty: float
    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    profit: float
    commission: float = 0.0
    mae: float | None = None
    mfe: float | None = None
    strategy: str = ""


class Breakdown(BaseModel):
    label: str
    trades: int
    net: float
    win_rate: float


class JournalStats(BaseModel):
    trades: int
    net: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float | None
    expectancy: float
    max_drawdown: float
    first: str = ""
    last: str = ""
    by_weekday: list[Breakdown] = []
    by_hour: list[Breakdown] = []
    by_instrument: list[Breakdown] = []
    by_side: list[Breakdown] = []


class JournalImport(BaseModel):
    added: int
    skipped: int
    """Already in the journal - importing the same export twice changes nothing."""
    unreadable: int


class JournalQuestion(BaseModel):
    question: str


class JournalAnswer(BaseModel):
    answer: str
    model_id: str | None = None
