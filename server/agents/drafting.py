"""Turning "every weekday at 7, check ES and tell me if the overnight range is over 30 points" -
or a chat where you did a thing once - into a workflow draft you review before it is saved.

Two halves, on purpose. The schedule is read by rules (`when.py`): it must be exactly right. The
name, the standing instruction and the tools come from the local model, which is good at that,
checked against the real tool catalogue so a draft can never ask for a tool that does not exist.
Nothing is saved here: the form shows the draft and you press Create.
"""

from __future__ import annotations

import json
import logging
import re

from server.agents import when
from server.chat import routing, thinking
from server.db import repo
from server.db.connection import Database
from server.graph import dag
from server.models.params import SamplingParams
from server.models.workflows import JobDraft
from server.providers.base import PromptMessage, Token
from server.providers.registry import ProviderRegistry
from server.settings import Settings
from server.tools import registry as tools

log = logging.getLogger("jarvis.agents.drafting")

DEFAULT_CRON = "0 9 * * *"
PROMPT = """Turn this request into a workflow that will run on its own, on a schedule, with no one
there to answer questions. Reply with JSON only:
{{"name": "<3-5 words>", "instruction": "<what to do each run, written to the assistant, \
self-contained, including what to report>", "tools": ["<tool names it needs>"]}}

Available tools:
{catalogue}

Leave the schedule out of the instruction: it is set separately.

Request:
{request}"""
KEYWORDS = {
    "forecast": ("forecast", " es ", " nq ", "futures", "market"),
    "home_devices": ("light", "door", "lock", "thermostat", "home", "temperature"),
    "home_control": ("turn on", "turn off", "switch", "lock the", "dim"),
    "read_file": ("file", "notes", "document", "folder"),
    "list_dir": ("folder", "directory", "files"),
    "write_file": ("save", "write", "log to", "append"),
    "http_get": ("website", "page", "url", "http", "check the site"),
    "run_shell": ("run the command", "script", "backup"),
}


def _catalogue() -> str:
    return "\n".join(f"- {t.name}: {t.summary}" for t in tools.catalogue())


def _guess_tools(text: str) -> list[str]:
    lowered = f" {text.lower()} "
    known = {t.name for t in tools.catalogue()}
    return [n for n, words in KEYWORDS.items() if n in known and any(w in lowered for w in words)]


def _parse(raw: str) -> dict[str, object] | None:
    match = re.search(r"\{.*\}", thinking.strip_all(raw), re.S)
    if not match:
        return None
    try:
        found = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    return found if isinstance(found, dict) else None


async def _ask(db: Database, registry: ProviderRegistry, settings: Settings, request: str) -> str:
    model_id = await routing.resolve_model_id(db, registry, settings, None)
    provider, model = await registry.resolve(model_id)
    prompt = PROMPT.format(catalogue=_catalogue(), request=request)
    params = SamplingParams(temperature=0.2, max_tokens=400, thinking=False, n_probs=0)
    chunks: list[str] = []
    async for item in provider.stream(
        [PromptMessage(role="user", content=prompt)],
        params,
        model_id=model.id,
        ctx_len=min(model.ctx_len_max, 8192),
    ):
        if isinstance(item, Token):
            chunks.append(item.text)
    return "".join(chunks)


async def draft(
    db: Database,
    registry: ProviderRegistry,
    settings: Settings,
    description: str,
    *,
    used_tools: list[str] | None = None,
) -> JobDraft:
    schedule = when.read(description)
    cron = schedule.cron if schedule else DEFAULT_CRON
    known = {t.name for t in tools.catalogue()}
    fallback_tools = used_tools if used_tools is not None else _guess_tools(description)
    name, prompt, chosen, note = "", "", fallback_tools, ""
    try:
        found = _parse(await _ask(db, registry, settings, description)) or {}
        name = str(found.get("name") or "").strip()
        prompt = str(found.get("instruction") or "").strip()
        raw_tools = found.get("tools")
        if isinstance(raw_tools, list) and used_tools is None:
            chosen = [str(t) for t in raw_tools if str(t) in known]
        if not prompt:
            note = "The model's draft could not be read, so this is your request as written."
    except Exception as exc:  # noqa: BLE001 - a draft without a model is still a draft
        log.warning("drafting: model unavailable: %s", exc)
        note = "No model was available, so this is your request as written. Edit it as you like."
    words = description.split()
    return JobDraft(
        name=(name or " ".join(words[:5]).rstrip(".,"))[:60],
        cron=cron,
        schedule=when.describe(cron),
        schedule_found=schedule is not None,
        prompt=prompt or description.strip(),
        tools=sorted(set(chosen)),
        note=note,
    )


def example(db: Database, conversation_id: str) -> tuple[str, list[str]]:
    """What you asked in a chat, and the tools that actually ran in it."""
    with db.session() as conn:
        conversation = repo.conversations.get(conn, conversation_id)
        messages = repo.messages.list_for_conversation(conn, conversation_id)
        used = [
            r["tool"]
            for r in conn.execute(
                "SELECT DISTINCT tc.tool FROM tool_calls tc JOIN job_runs jr"
                " ON jr.id = tc.job_run_id WHERE jr.conversation_id = ? AND tc.status = 'ran'",
                (conversation_id,),
            )
        ]
    leaf = conversation.active_leaf_id if conversation else None
    path = dag.ancestors(messages, leaf) if leaf else messages
    asks = [
        m.content.strip()
        for m in path
        if m.role == "user" and '<context source="tool:' not in m.content and m.content.strip()
    ]
    request = "In a chat, I asked for this - make it a workflow that does it again:\n" + "\n".join(
        f"- {a[:500]}" for a in asks[:6]
    )
    return request, used
