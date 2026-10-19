"""Which model answers: what you asked for, what you pinned, or - in Smart mode - the best model
on this PC for this particular message.

Smart mode reads the message, names what kind of question it is, and picks among the local models
that fit. Every pick comes with a plain sentence saying why, stored on the answer, because a router
you cannot see is a router you cannot trust. The rules are deliberately readable:

- Your own Council verdicts win first: a model that keeps winning a category is chosen for it.
- Code goes to a coding model, hard reasoning to a reasoning model or the strongest one, a long
  paste to the model with the most context, a short question to the fastest.
- Otherwise the model already answering this chat keeps answering, so nothing reloads for nothing.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Literal

from server.db import repo
from server.db.connection import Database
from server.errors import Remedy, SovereignError
from server.hardware import probe, selection
from server.hardware.selection import infer_params_b
from server.models.hardware import ModelOption
from server.providers.registry import ProviderRegistry
from server.settings import Settings

SMART = "smart"
"""The picker value for "choose per message". Stored like any pinned model id."""

Category = Literal["code", "reasoning", "long", "quick", "creative", "general"]

LABEL: dict[Category, str] = {
    "code": "a coding question",
    "reasoning": "a question that needs careful reasoning",
    "long": "a long text",
    "quick": "a quick question",
    "creative": "a writing task",
    "general": "a general question",
}

CODE = re.compile(
    r"```|\b(def|class|function|const|import|return|SELECT|traceback|stack trace|exception|regex|"
    r"compile[sd]?|refactor|debug|bug|python|javascript|typescript|rust|golang|java|c\+\+|sql|"
    r"bash|powershell|api|json|yaml|html|css|react|script|code)\b",
    re.IGNORECASE,
)
REASONING = re.compile(
    r"\b(prove|proof|calculate|compute|solve|derive|equation|probability|integral|optimi[sz]e|"
    r"step by step|logic|puzzle|riddle|how many|trade-?offs?|strategy|analy[sz]e|why does)\b"
    r"|\d+\s*[-+*/^]\s*\d+",
    re.IGNORECASE,
)
CREATIVE = re.compile(
    r"\b(write|draft|rewrite|compose)\b.{0,40}\b(story|poem|song|email|letter|post|essay|speech|"
    r"tweet|caption|lyrics|bio)\b|\b(poem|haiku|short story)\b",
    re.IGNORECASE,
)
CODER = re.compile(r"cod(er|e|estral)|starcoder|devstral", re.IGNORECASE)
REASONER = re.compile(r"\b(r1|qwq|reason\w*|think\w*|o1|magistral)\b|-r1", re.IGNORECASE)
LONG_CHARS = 6000
QUICK_CHARS = 80
TRUST_AFTER = 3
"""Council rounds a model must have sat in a category before its win rate steers the router."""


def classify(text: str) -> Category:
    text = text.strip()
    if len(text) >= LONG_CHARS:
        return "long"
    if CODE.search(text):
        return "code"
    if REASONING.search(text):
        return "reasoning"
    if CREATIVE.search(text):
        return "creative"
    if len(text) <= QUICK_CHARS:
        return "quick"
    return "general"


@dataclass
class Route:
    model_id: str | None
    note: str = ""
    """Why this model answered, in one sentence. Empty when you chose the model yourself."""


def _name(option: ModelOption) -> str:
    return option.model.display_name or option.model.id


def pick(
    options: list[ModelOption],
    category: Category,
    *,
    scores: dict[str, tuple[int, int]],
    previous: str | None,
) -> Route:
    """Choose among ranked options (best first). `scores` maps model id -> (wins, appearances)."""
    local = [o for o in options if not o.remote]
    pool = [o for o in local if o.status in ("fits", "tight")] or local
    if not pool:
        return Route(None)
    what = LABEL[category]
    if len(pool) == 1:
        return Route(
            pool[0].model.id, f"{what.capitalize()}; {_name(pool[0])} is the only model that fits."
        )

    trusted = [
        (o, scores[o.model.id]) for o in pool if scores.get(o.model.id, (0, 0))[1] >= TRUST_AFTER
    ]
    if trusted:
        option, (wins, seen) = max(trusted, key=lambda t: (t[1][0] / t[1][1], t[1][1]))
        if wins:
            return Route(
                option.model.id,
                f"{what.capitalize()}; {_name(option)} won {wins} of {seen} Council rounds"
                " on these.",
            )

    if category == "code" and (
        coder := next((o for o in pool if CODER.search(o.model.id + o.model.display_name)), None)
    ):
        return Route(coder.model.id, f"{what.capitalize()}, so a coding model: {_name(coder)}.")
    if category == "reasoning":
        option = next(
            (o for o in pool if REASONER.search(o.model.id + " " + o.model.display_name)), pool[0]
        )
        return Route(
            option.model.id,
            f"{what.capitalize()}, so the strongest reasoner here: {_name(option)}.",
        )
    if category == "long":
        option = max(pool, key=lambda o: (o.recommended_ctx_len, -pool.index(o)))
        return Route(
            option.model.id,
            f"{what.capitalize()}, so the most room to read it: {_name(option)}"
            f" ({option.recommended_ctx_len // 1024}K).",
        )

    if previous and (same := next((o for o in pool if o.model.id == previous), None)):
        return Route(
            same.model.id, f"{what.capitalize()}; {_name(same)} is already answering this chat."
        )
    if category == "quick":
        option = min(pool, key=lambda o: infer_params_b(o.model) or float("inf"))
        return Route(
            option.model.id, f"{what.capitalize()}, so the fastest model: {_name(option)}."
        )
    return Route(
        pool[0].model.id,
        f"{what.capitalize()}, so the strongest model that fits: {_name(pool[0])}.",
    )


def _scores(conn: sqlite3.Connection, category: Category) -> dict[str, tuple[int, int]]:
    rows = conn.execute(
        "SELECT model_id, wins, appearances FROM model_scores WHERE category = ?", (category,)
    )
    return {r["model_id"]: (r["wins"], r["appearances"]) for r in rows}


def _previous(conn: sqlite3.Connection, conversation_id: str | None) -> str | None:
    if not conversation_id:
        return None
    row = conn.execute(
        "SELECT model_id FROM messages WHERE conversation_id = ? AND role = 'assistant'"
        " AND model_id IS NOT NULL ORDER BY created_at DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    return row["model_id"] if row else None


async def ranked(registry: ProviderRegistry, settings: Settings) -> list[ModelOption]:
    gpus, _ = probe.probe_gpus()
    return selection.rank(
        await registry.models(),
        gpu=gpus[0] if gpus else None,
        browser_reserve_mb=settings.hardware.browser_vram_reserve_mb,
        kv_dtype=settings.hardware.kv_cache_dtype,
    )


async def route(
    db: Database,
    registry: ProviderRegistry,
    settings: Settings,
    requested: str | None,
    *,
    text: str = "",
    conversation_id: str | None = None,
    needs_vision: bool = False,
) -> Route:
    """In order: what the request asked for, what you pinned, Smart mode, what fits.

    A pinned model that is no longer reachable - you closed LM Studio, llama.cpp is serving
    something else - silently falls back to the automatic choice rather than failing the request.
    Switching backends should not mean editing settings.
    """
    if requested and requested != SMART and not needs_vision:
        return Route(requested)
    with db.session() as conn:
        pinned = repo.settings.get(conn, repo.settings.SELECTED_MODEL)
    smart = requested == SMART or pinned == SMART
    options = await ranked(registry, settings)
    if needs_vision:
        chosen = requested if requested and requested != SMART else pinned
        return seeing(options, None if chosen == SMART else chosen)
    if not smart and pinned and any(o.model.id == pinned for o in options):
        return Route(str(pinned))
    if smart and text:
        category = classify(text)
        with db.session() as conn:
            scores, previous = _scores(conn, category), _previous(conn, conversation_id)
        chosen = pick(options, category, scores=scores, previous=previous)
        if chosen.model_id:
            return chosen
    choice = selection.best(options)
    return Route(choice.model.id if choice else None)


def seeing(options: list[ModelOption], preferred: str | None) -> Route:
    """A message with an image needs a model that can see: the one you chose if it can, else the
    best one that can - and if none is running, say exactly that rather than answer blind."""
    if preferred and any(o.model.id == preferred and o.model.supports_vision for o in options):
        return Route(preferred)
    seers = [o for o in options if o.model.supports_vision]
    if not seers:
        raise SovereignError(
            "provider_incapable",
            "This message has an image, and no model that can see is running. Download"
            ' "Gemma 3 4B (sees images)" in Settings > Models on this PC, or load a vision model'
            " in Ollama or LM Studio.",
            remedy=Remedy(label="Choose a model", action="choose_model"),
        )
    best = seers[0]
    return Route(
        best.model.id, f"This message has an image, so a model that can see: {_name(best)}."
    )


async def resolve_model_id(
    db: Database, registry: ProviderRegistry, settings: Settings, requested: str | None
) -> str | None:
    """The model for work that is not a chat message (file edits, previews): no routing note."""
    return (await route(db, registry, settings, requested)).model_id
