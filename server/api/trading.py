"""The trading co-pilot: the live feed from NinjaTrader, alerts, and your trade journal."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from server import paths
from server.chat import routing, thinking
from server.context.assembler import as_data
from server.deps import State
from server.errors import SovereignError
from server.models.params import SamplingParams
from server.models.trading import (
    AlertRule,
    AlertRuleCreate,
    JournalAnswer,
    JournalImport,
    JournalQuestion,
    JournalStats,
    LiveStatus,
    Trade,
)
from server.providers.base import PromptMessage, Token
from server.trading import alerts, journal

router = APIRouter(prefix="/api/trading", tags=["trading"])
MAX_IMPORT_MB = 20
ASK = """Answer my question about my own trading from the journal below. Use the numbers as given
and quote them; never invent trades. If the journal cannot answer it, say what it would take.
Be direct and brief.

{data}

Question: {question}"""


@router.get("/live")
def live(state: State) -> LiveStatus:
    assert state.copilot is not None
    return state.copilot.status()


@router.get("/ninjascript")
def ninjascript() -> FileResponse:
    """The JarvisFeed indicator, to drop into NinjaTrader's Custom/Indicators folder."""
    source = paths.resource("server", "trading", "ninjascript", "JarvisFeed.cs")
    return FileResponse(source, filename="JarvisFeed.cs", media_type="text/plain")


@router.get("/alerts")
def list_alerts(state: State) -> list[AlertRule]:
    with state.db.session() as conn:
        return alerts.rules(conn)


@router.post("/alerts")
def add_alert(body: AlertRuleCreate, state: State) -> AlertRule:
    with state.db.session() as conn:
        rule = alerts.add(conn, body)
    # Judged against the bars already here, not only the next one: "tell me if ES is above 5850"
    # when it already is should say so now.
    if state.copilot and rule.symbol in state.copilot.feed.latest:
        state.copilot.judge(rule.symbol)
    return rule


@router.delete("/alerts/{rule_id}")
def remove_alert(rule_id: str, state: State) -> None:
    with state.db.session() as conn:
        alerts.remove(conn, rule_id)


@router.post("/alerts/events/read")
def read_events(state: State) -> None:
    with state.db.session() as conn:
        alerts.mark_read(conn)


@router.post("/journal/import")
async def import_journal(request: Request, state: State) -> JournalImport:
    body = await request.body()
    if len(body) > MAX_IMPORT_MB * 1_000_000:
        raise SovereignError("invalid_request", f"That file is over {MAX_IMPORT_MB}MB.")
    trades, bad = journal.parse(body.decode("utf-8-sig", errors="replace"))
    if not trades:
        raise SovereignError(
            "invalid_request",
            "No trades found. Export them from NinjaTrader: Trade Performance > Trades, right-click"
            " > Export.",
        )
    with state.db.session() as conn:
        return journal.save(conn, trades, bad)


@router.get("/journal")
def journal_stats(state: State) -> JournalStats:
    with state.db.session() as conn:
        return journal.stats(journal.load(conn))


@router.get("/journal/trades")
def journal_trades(state: State, limit: int = 50) -> list[Trade]:
    with state.db.session() as conn:
        return list(reversed(journal.load(conn)))[:limit]


@router.delete("/journal")
def clear_journal(state: State) -> None:
    with state.db.session() as conn:
        conn.execute("DELETE FROM trades")


@router.post("/journal/ask")
async def ask(body: JournalQuestion, state: State) -> JournalAnswer:
    with state.db.session() as conn:
        trades = journal.load(conn)
    if not trades:
        return JournalAnswer(
            answer="Your journal is empty. Import a NinjaTrader trade export first."
        )
    summary = journal.stats(trades).model_dump_json(indent=1)
    rows = "\n".join(
        f"{t.entry_time},{t.exit_time},{t.instrument},{t.side},{t.qty:g},{t.entry_price:g},"
        f"{t.exit_price:g},{t.profit:.2f}"
        for t in trades[-300:]
    )
    data = (
        as_data("journal:stats", summary)
        + "\n\n"
        + as_data(
            "journal:trades", "entry,exit,instrument,side,qty,entry_price,exit_price,net\n" + rows
        )
    )
    model_id = await routing.resolve_model_id(state.db, state.registry, state.settings, None)
    provider, model = await state.registry.resolve(model_id)
    params = SamplingParams(temperature=0.2, max_tokens=600, n_probs=0)
    chunks: list[str] = []
    async for item in provider.stream(
        [PromptMessage(role="user", content=ASK.format(data=data, question=body.question))],
        params,
        model_id=model.id,
        ctx_len=min(model.ctx_len_max, 16384),
    ):
        if isinstance(item, Token):
            chunks.append(item.text)
    return JournalAnswer(answer=thinking.strip_all("".join(chunks)).strip(), model_id=model.id)
