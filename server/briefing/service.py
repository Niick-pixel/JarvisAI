"""The morning briefing: gather the facts, have the local model write them up, keep the result.

It is written on a schedule you set (or on demand), stored as a chat so you can ask about it, and
shown on the Home screen. If no model is reachable the facts are still delivered, as plain lines -
a briefing that fails because the model is not loaded yet would fail exactly when you need it.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from server.briefing import gather
from server.chat import routing, thinking
from server.context.assembler import as_data
from server.db import repo
from server.db.connection import Database
from server.home.hub import Hub
from server.ids import new_id, now_ms
from server.models.briefing import Briefing, BriefingSection, BriefingSettings
from server.models.conversation import ConversationCreate
from server.models.params import SamplingParams
from server.providers.base import PromptMessage, Token
from server.providers.registry import ProviderRegistry
from server.settings import Settings

if TYPE_CHECKING:
    from server.deps import AppState

log = logging.getLogger("jarvis.briefing")

SETTINGS_KEY = "briefing"
TITLES = {"markets": "Markets", "home": "Home", "agents": "From your agents"}
PROMPT = """Write my morning briefing from the facts below. Plain, warm, and short: a one-line
greeting, then one short paragraph per section that has something worth saying, most important
first. Use the numbers as given; never invent any. If a section says something needs attention,
say so plainly. No headings, no bullet lists, under 180 words.

{facts}"""


def load_settings(db: Database) -> BriefingSettings:
    with db.session() as conn:
        raw = repo.settings.get(conn, SETTINGS_KEY)
    return BriefingSettings(**raw) if isinstance(raw, dict) else BriefingSettings()


def save_settings(db: Database, value: BriefingSettings) -> None:
    with db.session() as conn:
        repo.settings.put(conn, SETTINGS_KEY, value.model_dump(exclude={"next_at"}))


def cron_for(value: BriefingSettings) -> str:
    hour, minute = value.time.split(":")
    return f"{int(minute)} {int(hour)} * * {'mon-fri' if value.days == 'weekdays' else '*'}"


def _row(row: dict[str, object]) -> Briefing:
    sections = json.loads(str(row.pop("sections_json") or "[]"))
    return Briefing(**row, sections=[BriefingSection(**s) for s in sections])  # type: ignore[arg-type]


def latest(db: Database, limit: int = 1) -> list[Briefing]:
    with db.session() as conn:
        rows = conn.execute(
            "SELECT * FROM briefings ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row(dict(r)) for r in rows]


def mark_read(db: Database, briefing_id: str) -> None:
    with db.session() as conn:
        conn.execute(
            "UPDATE briefings SET read_at = COALESCE(read_at, ?) WHERE id = ?",
            (now_ms(), briefing_id),
        )


class Briefings:
    def __init__(self, state: AppState) -> None:
        self.state = state

    @property
    def db(self) -> Database:
        return self.state.db

    @property
    def registry(self) -> ProviderRegistry:
        return self.state.registry

    @property
    def settings(self) -> Settings:
        return self.state.settings

    @property
    def hub(self) -> Hub | None:
        return self.state.home

    async def sections(self, wanted: list[str]) -> list[BriefingSection]:
        previous = latest(self.db)
        since = previous[0].created_at if previous else now_ms() - gather.DAY * 1000
        found: dict[str, str] = {}
        if "markets" in wanted:
            found["markets"] = await gather.markets(self.settings)
        if "home" in wanted:
            found["home"] = await gather.home(self.hub)
        if "agents" in wanted:
            found["agents"] = gather.agents(self.db, since)
        return [
            BriefingSection(key=k, title=TITLES[k], facts=v)  # type: ignore[arg-type]
            for k, v in found.items()
            if v
        ]

    async def _write(self, sections: list[BriefingSection]) -> tuple[str, str | None]:
        """The model's write-up, and which model wrote it. Falls back to the facts themselves."""
        plain = "\n\n".join(f"{s.title}\n{s.facts}" for s in sections)
        if not sections:
            return "Good morning. Nothing new to report: no market data, home or agent news.", None
        try:
            model_id = await routing.resolve_model_id(self.db, self.registry, self.settings, None)
            provider, model = await self.registry.resolve(model_id)
            facts = "\n\n".join(as_data(f"briefing:{s.key}", s.facts) for s in sections)
            prompt = [PromptMessage(role="user", content=PROMPT.format(facts=facts))]
            params = SamplingParams(temperature=0.4, max_tokens=400, thinking=False, n_probs=0)
            chunks: list[str] = []
            async for item in provider.stream(
                prompt, params, model_id=model.id, ctx_len=min(model.ctx_len_max, 8192)
            ):
                if isinstance(item, Token):
                    chunks.append(item.text)
            text = thinking.strip_all("".join(chunks)).strip()
            return (text or plain), model.id
        except Exception as exc:  # noqa: BLE001 - the facts still go out without a model
            log.warning("briefing: write-up failed, sending the facts as they are: %s", exc)
            return plain, None

    async def run(self) -> Briefing:
        wanted = load_settings(self.db).sections
        sections = await self.sections(list(wanted))
        body, model_id = await self._write(sections)
        title = f"Briefing · {datetime.now().strftime('%a %d %b')}"
        with self.db.session() as conn:
            conversation = repo.conversations.create(conn, ConversationCreate(title=title))
            ask = repo.messages.create(
                conn, conversation_id=conversation.id, role="user", content="Brief me."
            )
            answer = repo.messages.create(
                conn,
                conversation_id=conversation.id,
                role="assistant",
                content=body,
                parent_id=ask.id,
                model_id=model_id,
            )
            repo.conversations.touch(conn, conversation.id, active_leaf_id=answer.id)
            briefing = Briefing(
                id=new_id("brf"),
                created_at=int(time.time() * 1000),
                title=title,
                body=body,
                sections=sections,
                conversation_id=conversation.id,
            )
            conn.execute(
                "INSERT INTO briefings (id, created_at, title, body, sections_json,"
                " conversation_id) VALUES (?,?,?,?,?,?)",
                (
                    briefing.id,
                    briefing.created_at,
                    title,
                    body,
                    json.dumps([s.model_dump() for s in sections]),
                    conversation.id,
                ),
            )
        return briefing
