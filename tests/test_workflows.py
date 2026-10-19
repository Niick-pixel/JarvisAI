"""Workflows by example: plain words - or a chat - become a draft you review, with the schedule read
by rules, the tools checked against the real catalogue, and nothing saved until you create it."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from conftest import FakeProvider
from fastapi.testclient import TestClient

from server.main import create_app
from server.providers.base import StreamItem
from server.providers.registry import ProviderRegistry
from server.settings import Settings

REPLY = (
    '{"name": "Overnight ES range", "instruction": "Forecast ES for the next hour and report'
    ' whether the overnight range was over 30 points.", "tools": ["forecast", "launch_missiles"]}'
)


class Drafter(FakeProvider):
    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        self.shown = messages[-1].content
        self.script = ["Sure:\n", REPLY]
        async for item in super().stream(messages, params, **kwargs):
            yield item


class Broken(FakeProvider):
    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        raise RuntimeError("no model loaded")
        yield  # pragma: no cover


def test_words_become_a_draft_and_nothing_is_saved(settings: Settings) -> None:
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([Drafter()])
    with TestClient(app) as client:
        draft = client.post(
            "/api/agents/drafts",
            json={"description": "every weekday at 7am check if the ES overnight range was big"},
        ).json()
        assert draft["cron"] == "0 7 * * 1-5" and draft["schedule"] == "Weekdays at 07:00"
        assert draft["schedule_found"] is True
        assert draft["name"] == "Overnight ES range"
        assert draft["prompt"].startswith("Forecast ES for the next hour")
        assert draft["tools"] == ["forecast"]  # a tool that does not exist is dropped
        assert client.get("/api/agents/jobs").json() == []


def test_without_a_model_the_draft_is_your_own_words(settings: Settings) -> None:
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([Broken()])
    with TestClient(app) as client:
        draft = client.post(
            "/api/agents/drafts", json={"description": "Check the front door lock and the lights"}
        ).json()
        assert draft["schedule_found"] is False and draft["cron"] == "0 9 * * *"
        assert draft["prompt"] == "Check the front door lock and the lights"
        assert "home_devices" in draft["tools"]
        assert "No model was available" in draft["note"]


def test_a_chat_becomes_a_workflow_with_the_tools_it_used(settings: Settings) -> None:
    drafter = Drafter()
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([drafter])
    with TestClient(app) as client:
        cid = client.post("/api/conversations", json={"title": "x"}).json()["id"]
        with app.state.app.db.session() as conn:
            from server.db import repo

            ask = repo.messages.create(
                conn, conversation_id=cid, role="user", content="list my notes folder"
            )
            repo.conversations.touch(conn, cid, active_leaf_id=ask.id)
            repo.agents.ensure_chat_job(conn, [])
            run_id = repo.agents.start_run(conn, repo.agents.CHAT_JOB_ID, cid)
            conn.execute(
                "INSERT INTO tool_calls (id, job_run_id, tool, args_json, status, created_at)"
                " VALUES ('call_1', ?, 'list_dir', '{}', 'ran', 0)",
                (run_id,),
            )
        draft = client.post(f"/api/agents/drafts/from-conversation/{cid}").json()
        assert "list my notes folder" in drafter.shown
        assert draft["tools"] == ["list_dir"]  # what actually ran, not what the model guessed


def test_the_dashboard_counts_each_workflows_runs(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        job = client.post(
            "/api/agents/jobs",
            json={"name": "Notes", "cron": "0 9 * * 1-5", "prompt": "summarise", "tools": []},
        ).json()
        app_db = client.app.state.app.db  # type: ignore[attr-defined]
        with app_db.session() as conn:
            for i, status in enumerate(["done", "failed", "done"]):
                conn.execute(
                    "INSERT INTO job_runs (id, job_id, status, started_at, finished_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (f"run_{i}", job["id"], status, 1000 * i, 1000 * i + 4000),
                )
        [stats] = client.get("/api/agents/dashboard").json()
        assert (stats["runs"], stats["ok"], stats["failed"]) == (3, 2, 1)
        assert stats["recent"] == ["done", "failed", "done"]
        assert stats["avg_seconds"] == 4.0
