"""Naming a conversation after what it is about, the way every chat app's sidebar does.

The first message gives an instant title - its opening words - so the sidebar is never a column
of "New conversation". Once the first answer exists, the model is asked for a short one with
thinking off; if that fails or comes back as nonsense, the instant title simply stays.
"""

from __future__ import annotations

import logging
import re

from server.chat import thinking
from server.db import repo
from server.db.connection import Database
from server.models.conversation import ConversationUpdate
from server.models.params import SamplingParams
from server.providers.base import ModelProvider, PromptMessage, Token

log = logging.getLogger(__name__)

PLACEHOLDERS = {"", "new conversation", "new chat"}
PROMPT = (
    "Write a title of 2 to 6 words for a conversation that starts with the message below. "
    "Reply with the title only: no quotes, no punctuation at the end.\n\nMessage: {message}"
)
MAX_CHARS = 48


def instant(message: str) -> str:
    """The first few words of the opening message, cut at a word boundary."""
    words = " ".join(message.split())
    if len(words) <= MAX_CHARS:
        return words
    return words[:MAX_CHARS].rsplit(" ", 1)[0] + "…"


def needs_title(title: str) -> bool:
    return title.strip().lower() in PLACEHOLDERS


def clean(raw: str) -> str:
    line = thinking.strip_all(raw).strip().splitlines()[0] if raw.strip() else ""
    line = re.sub(r"^(title:\s*)", "", line, flags=re.IGNORECASE)
    line = line.strip(" \"'*#.!?:;`“”")
    return line if 2 <= len(line) <= MAX_CHARS else ""


async def refine(
    db: Database, provider: ModelProvider, *, conversation_id: str, model_id: str, message: str
) -> None:
    """Ask the model for a better title. Only replaces the instant one, never a title you set."""
    params = SamplingParams(seed=5, temperature=0.3, max_tokens=24, n_probs=0, thinking=False)
    chunks: list[str] = []
    try:
        async for item in provider.stream(
            [PromptMessage(role="user", content=PROMPT.format(message=message[:600]))],
            params,
            model_id=model_id,
            ctx_len=2048,
        ):
            if isinstance(item, Token):
                chunks.append(item.text)
    except Exception as exc:  # noqa: BLE001 - a title is never worth failing a turn over
        log.info("titles: model title failed, keeping the instant one: %s", exc)
        return
    title = clean("".join(chunks))
    if not title:
        return
    with db.session() as conn:
        current = repo.conversations.get(conn, conversation_id)
        if current is not None and current.title == instant(message):
            repo.conversations.update(conn, conversation_id, ConversationUpdate(title=title))
