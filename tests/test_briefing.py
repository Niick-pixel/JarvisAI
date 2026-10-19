"""The morning briefing: gathered from facts, written by the local model, kept as a chat - and
still delivered, as the plain facts, when no model can write it up."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from conftest import FakeProvider
from fastapi.testclient import TestClient

from server.main import create_app
from server.providers.base import StreamItem
from server.providers.registry import ProviderRegistry
from server.settings import Settings


class Writer(FakeProvider):
    """Writes the briefing and remembers what it was shown."""

    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        self.shown = messages[-1].content
        self.script = ["Good morning. ", "Your nightly ", "backup agent finished cleanly."]
        async for item in super().stream(messages, params, **kwargs):
            yield item


class Broken(FakeProvider):
    async def stream(self, messages: Any, params: Any, **kwargs: Any) -> AsyncIterator[StreamItem]:
        raise RuntimeError("model not loaded yet")
        yield  # pragma: no cover


def seed_inbox(app: Any) -> None:
    from server.db import repo

    with app.state.app.db.session() as conn:
        repo.agents.add_inbox(
            conn, job_run_id=None, title="Nightly backup", body="All 3 folders copied.", flags=[]
        )


def test_settings_put_the_briefing_on_the_clock(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        off = client.get("/api/briefing/settings").json()
        assert off["enabled"] is False and off["next_at"] is None
        on = client.put(
            "/api/briefing/settings", json={**off, "enabled": True, "time": "06:45"}
        ).json()
        assert on["enabled"] is True and on["time"] == "06:45" and on["next_at"]
        assert (
            client.put("/api/briefing/settings", json={**off, "time": "25:00"}).status_code == 422
        )


def test_a_briefing_is_written_from_the_facts_and_kept_as_a_chat(settings: Settings) -> None:
    writer = Writer()
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([writer])
    with TestClient(app) as client:
        seed_inbox(app)
        briefing = client.post("/api/briefing/run").json()

        assert briefing["body"] == "Good morning. Your nightly backup agent finished cleanly."
        [section] = briefing["sections"]  # no market data, no Home Assistant: just the agents
        assert section["key"] == "agents" and "All 3 folders copied." in section["facts"]
        # The facts reach the model as data, inside the standard envelope.
        assert '<context source="briefing:agents">' in writer.shown

        chat = client.get(f"/api/conversations/{briefing['conversation_id']}").json()
        by_role = {m["role"]: m for m in chat["messages"]}
        assert by_role["assistant"]["parent_id"] == by_role["user"]["id"]
        assert by_role["assistant"]["content"] == briefing["body"]

        assert client.get("/api/briefing/latest").json()["id"] == briefing["id"]
        client.post(f"/api/briefing/{briefing['id']}/read")
        assert client.get("/api/briefing/latest").json()["read_at"]


def test_without_a_model_the_facts_still_arrive(settings: Settings) -> None:
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([Broken()])
    with TestClient(app) as client:
        seed_inbox(app)
        briefing = client.post("/api/briefing/run").json()
        assert briefing["body"].startswith(
            "From your agents\nNightly backup: All 3 folders copied."
        )


def test_the_facts_say_what_needs_attention() -> None:
    from server.briefing import gather
    from server.forecast.ninjatrader import Bar
    from server.models.home import Device

    day = 86_400
    bars = [Bar(t=0, o=1, h=1, low=1, c=5000.0, v=1), Bar(t=day, o=1, h=1, low=1, c=5050.0, v=1)]
    assert gather._change(bars) == ", +50.00 (+1.00%) over 24 hours"
    assert gather._change(bars[:1]) == ""  # no day-old bar to compare with: say nothing

    def dev(name: str, domain: str, state: str, **kw: Any) -> Device:
        return Device(
            entity_id=f"{domain}.{name}",
            name=name,
            domain=domain,
            area="Hall",
            state=state,
            available=kw.pop("available", True),
            actions=[],
            **kw,
        )

    lines = gather._home_lines(
        [
            dev("Porch", "light", "on"),
            dev("Kitchen", "light", "off"),
            dev("Front door", "lock", "unlocked"),
            dev("Thermostat", "climate", "heat", current=19.5, target=21, unit="°C"),
            dev("Garage sensor", "sensor", "unavailable", available=False),
        ]
    )
    assert lines == [
        "Lights on: Porch (Hall)",
        "Unlocked: Front door",
        "Thermostat: 19.5°C, set to 21 (heat)",
        "Not responding: Garage sensor",
    ]
