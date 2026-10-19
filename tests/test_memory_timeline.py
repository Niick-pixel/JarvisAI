"""The memory timeline: every learned memory knows the chat that taught it, shows where it has
been used since, and can be forgotten - alone or with everything else that chat taught - and put
back exactly as it was."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from conftest import FakeProvider
from fastapi.testclient import TestClient

from server.main import create_app
from server.providers.base import StreamItem
from server.providers.registry import ProviderRegistry
from server.settings import Settings

FACT = "The user trades ES futures on the five minute chart."
ANSWER = ["Five-minute ES bars ", "suit a day trader ", "who wants several setups a session."]


class Learner(FakeProvider):
    """Answers chat turns from its script; answers the extraction prompt with one fact."""

    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        extracting = "durable facts" in messages[-1].content
        self.script = [FACT] if extracting else list(ANSWER)
        async for item in super().stream(messages, params, **kwargs):
            yield item


def chat(client: TestClient, cid: str, content: str) -> str:
    with client.stream(
        "POST", "/api/chat/stream", json={"conversation_id": cid, "content": content}
    ) as response:
        b"".join(response.iter_bytes())
    answer = client.get(f"/api/conversations/{cid}").json()["messages"][-1]["id"]
    client.get(f"/api/memory/batches/for-message/{answer}")  # wait for capture
    return str(answer)


def test_a_learned_memory_links_back_to_its_chat_and_forgets_with_undo(settings: Settings) -> None:
    settings.memory.min_answer_chars = 10
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([Learner()])
    with TestClient(app) as client:
        cid = client.post("/api/conversations", json={"title": "Charts"}).json()["id"]
        message = chat(client, cid, "Which timeframe should I trade ES futures on?")

        [entry] = client.get("/api/memory").json()
        assert entry["content"] == FACT
        assert entry["source_conversation_id"] == cid
        assert entry["source_message_id"] == message
        assert entry["source_title"]
        # The file is the truth: the link is written into it, so a rescan keeps it.
        path = settings.paths.memory_dir / entry["path"]
        assert f"from: {cid} {message}" in path.read_text()

        # Used again in a second chat: the timeline says where.
        other = client.post("/api/conversations", json={"title": "Later"}).json()["id"]
        chat(client, other, "Remind me how I trade ES futures")
        uses = client.get(f"/api/memory/{entry['id']}/uses").json()
        assert [u["conversation_id"] for u in uses] == [other]

        # Forget everything the first chat taught, then undo it.
        gone = client.delete(f"/api/memory/from-conversation/{cid}").json()
        assert [g["id"] for g in gone] == [entry["id"]]
        assert client.get("/api/memory").json() == []
        assert not path.exists()

        client.post("/api/memory/restore", json=gone)
        [back] = client.get("/api/memory").json()
        assert (back["id"], back["content"], back["source_conversation_id"]) == (
            entry["id"],
            FACT,
            cid,
        )
