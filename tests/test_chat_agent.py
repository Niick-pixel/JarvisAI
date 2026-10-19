"""Agent mode in chat: a turn that asks for a tool waits for you, runs it, reads the result and
answers - in the chat, never in the Inbox, under the same gate as every scheduled job."""

from __future__ import annotations

import dataclasses
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from conftest import FakeProvider
from fastapi.testclient import TestClient

from server.main import create_app
from server.providers.base import StreamItem
from server.providers.registry import ProviderRegistry
from server.settings import Settings

WRITE = '```tool\n{"tool": "write_file", "args": {"path": "notes.txt", "content": "hi"}}\n```'


class Scripted(FakeProvider):
    """One script per generation, in order: the tool call first, the answer after the result."""

    def __init__(self, turns: list[list[str]]) -> None:
        super().__init__()
        self.turns = turns

    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        self.script = self.turns.pop(0) if self.turns else ["(no more turns)"]
        async for item in super().stream(messages, params, **kwargs):
            yield item


def wait_for(client: TestClient, run_id: str, *statuses: str) -> dict[str, Any]:
    for _ in range(200):
        turn = client.get(f"/api/chat/agent/{run_id}").json()
        if turn["status"] in statuses:
            return turn
        time.sleep(0.02)
    raise AssertionError(f"turn stayed {turn['status']}")


def test_a_tool_turn_waits_for_approval_then_answers_in_the_chat(
    settings: Settings, tmp_path: Path
) -> None:
    settings.agents.workspace = tmp_path / "workspace"
    provider = Scripted([[WRITE], ["Done: ", "wrote notes.txt."]])
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([provider])
    with TestClient(app) as client:
        agents = app.state.app.chat_agents
        agents.rt = dataclasses.replace(agents.rt, registry=ProviderRegistry([provider]))
        cid = client.post("/api/conversations", json={"title": "New conversation"}).json()["id"]
        started = client.post(
            "/api/chat/agent", json={"conversation_id": cid, "content": "save a note"}
        ).json()

        parked = wait_for(client, started["run_id"], "waiting_approval")
        [call] = parked["calls"]
        assert call["tool"] == "write_file" and call["status"] == "pending"
        workspace = settings.agents.workspace / "chat"
        assert not (workspace / "notes.txt").exists()  # nothing happens before you say yes

        client.post(f"/api/tools/calls/{call['id']}", json={"approve": True})
        done = wait_for(client, started["run_id"], "done", "failed")
        assert done["status"] == "done", done["error"]
        assert (workspace / "notes.txt").read_text() == "hi"

        messages = client.get(f"/api/conversations/{cid}").json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
        assert messages[-1]["content"] == "Done: wrote notes.txt."
        assert "tool:write_file" in messages[2]["content"]  # the result, delivered as data
        # The hidden chat job stays hidden, and a chat turn never reports to the Inbox.
        assert all(j["id"] != "job_chat" for j in client.get("/api/agents/jobs").json())
        assert client.get("/api/agents/inbox").json() == []


def test_stopping_a_turn_denies_what_waits_and_runs_nothing(
    settings: Settings, tmp_path: Path
) -> None:
    settings.agents.workspace = tmp_path / "workspace"
    provider = Scripted([[WRITE]])
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([provider])
    with TestClient(app) as client:
        agents = app.state.app.chat_agents
        agents.rt = dataclasses.replace(agents.rt, registry=ProviderRegistry([provider]))
        cid = client.post("/api/conversations", json={"title": "New conversation"}).json()["id"]
        run_id = client.post(
            "/api/chat/agent", json={"conversation_id": cid, "content": "save a note"}
        ).json()["run_id"]
        wait_for(client, run_id, "waiting_approval")

        client.post(f"/api/chat/agent/{run_id}/stop")
        stopped = wait_for(client, run_id, "cancelled")
        assert [c["status"] for c in stopped["calls"]] == ["denied"]
        assert client.get("/api/tools/calls?only_pending=true").json() == []
        assert not (settings.agents.workspace / "chat" / "notes.txt").exists()
