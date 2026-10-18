"""Home Assistant, against a fake one: connecting, devices by room, actions as service calls, and
chat commands that Home Assistant answers instead of the model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from server.home import devices
from server.main import create_app
from server.models.home import HomeActionRequest
from server.settings import load_settings

HA = "http://ha.test:8123"
TOKEN = "secret-token"


def entity(entity_id: str, state: str, name: str = "", **attrs: Any) -> dict[str, Any]:
    return {"entity_id": entity_id, "state": state, "attributes": {"friendly_name": name, **attrs}}


STATES = [
    entity("light.kitchen", "on", "Kitchen", brightness=128),
    entity(
        "climate.hall",
        "heat",
        "Thermostat",
        temperature=21,
        current_temperature=19.5,
        hvac_action="heating",
    ),
    entity("sensor.cpu", "40", "CPU", device_class="power"),
    entity("binary_sensor.front", "off", "Front door", device_class="door"),
    entity("sun.sun", "above_horizon"),
    entity("lock.front", "locked", "Front lock"),
]
AREAS = [["light.kitchen", "Kitchen"], ["climate.hall", "Hallway"], ["lock.front", "Hallway"]]


class FakeHA:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.agents_known = {"conversation.home_assistant"}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, text="401: Unauthorized")
        path = request.url.path
        body = json.loads(request.content or b"null")
        if path == "/api/config":
            return httpx.Response(200, json={"location_name": "Casa", "version": "2026.10.1"})
        if path == "/api/states":
            return httpx.Response(200, json=STATES)
        if path == "/api/template":
            return httpx.Response(200, text=json.dumps(AREAS))
        if path.startswith("/api/services/"):
            self.calls.append((path.removeprefix("/api/services/"), body))
            return httpx.Response(200, json=[])
        if path == "/api/conversation/process":
            if body["agent_id"] not in self.agents_known:
                return httpx.Response(400, json={"message": "agent not found"})
            if "light" in body["text"]:
                speech = {"plain": {"speech": "Turned off the lights"}}
                return httpx.Response(
                    200, json={"response": {"response_type": "action_done", "speech": speech}}
                )
            miss = {"response_type": "error", "data": {"code": "no_intent_match"}, "speech": {}}
            return httpx.Response(200, json={"response": miss})
        return httpx.Response(404)


@pytest.fixture
def ha(monkeypatch: pytest.MonkeyPatch) -> FakeHA:
    fake = FakeHA()
    real = httpx.AsyncClient

    def client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(fake)
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", client)
    return fake


@pytest.fixture
def app(tmp_path: Path, ha: FakeHA):  # type: ignore[no-untyped-def]
    settings = load_settings(paths={"data_dir": tmp_path, "memory_dir": tmp_path / "memory"})
    with TestClient(create_app(settings)) as client:
        yield client


def connect(app: TestClient) -> None:
    response = app.put("/api/home/connection", json={"url": f"{HA}/", "token": TOKEN})
    assert response.status_code == 200, response.text
    assert response.json()["connected"] and response.json()["name"] == "Casa"


def test_an_address_without_a_scheme_is_taken_as_http(app: TestClient) -> None:
    response = app.put("/api/home/connection", json={"url": "ha.test:8123", "token": TOKEN})
    assert response.json()["url"] == HA


def test_a_wrong_token_is_refused_and_not_saved(app: TestClient, tmp_path: Path) -> None:
    response = app.put("/api/home/connection", json={"url": HA, "token": "nope"})
    assert response.status_code == 400 and "token" in response.json()["message"]
    assert not (tmp_path / "home.json").exists()
    assert app.get("/api/home/status").json()["configured"] is False


def test_devices_come_grouped_by_room_without_the_noise(app: TestClient) -> None:
    connect(app)
    found = app.get("/api/home/devices").json()
    ids = [d["entity_id"] for d in found]
    assert "sun.sun" not in ids and "sensor.cpu" not in ids  # not things a home app shows
    assert ids[:3] == ["lock.front", "climate.hall", "light.kitchen"]  # Hallway by name, Kitchen
    light = next(d for d in found if d["entity_id"] == "light.kitchen")
    assert light["level"] == 50 and light["area"] == "Kitchen"
    climate = next(d for d in found if d["entity_id"] == "climate.hall")
    assert (climate["target"], climate["current"], climate["detail"]) == (21, 19.5, "heating")
    door = next(d for d in found if d["entity_id"] == "binary_sensor.front")
    assert door["area"] == "Other" and door["actions"] == [] and door["kind"] == "door"


def test_actions_become_service_calls(app: TestClient, ha: FakeHA) -> None:
    connect(app)
    body = {"entity_id": "light.kitchen", "action": "brightness", "value": 30}
    assert app.post("/api/home/action", json=body).status_code == 200
    assert ha.calls[-1] == ("light/turn_on", {"entity_id": "light.kitchen", "brightness_pct": 30})
    bad = app.post(
        "/api/home/action", json={"entity_id": "lock.front", "action": "brightness", "value": 1}
    )
    assert bad.status_code == 400
    assert devices.service(
        HomeActionRequest(entity_id="media_player.tv", action="volume", value=40)
    ) == (
        "media_player",
        "volume_set",
        {"entity_id": "media_player.tv", "volume_level": 0.4},
    )


def test_a_home_command_in_chat_is_answered_by_home_assistant(app: TestClient) -> None:
    connect(app)
    cid = app.post("/api/conversations", json={"title": "New conversation"}).json()["id"]
    result = app.post(
        "/api/home/assist", json={"text": "turn off the lights", "conversation_id": cid}
    ).json()
    assert result == {"handled": True, "reply": "Turned off the lights", "conversation_id": cid}
    tree = app.get(f"/api/conversations/{cid}").json()
    turns = [(m["role"], m["content"], m["model_id"]) for m in tree["messages"]]
    assert turns == [
        ("user", "turn off the lights", None),
        ("assistant", "Turned off the lights", "home-assistant"),
    ]
    assert tree["conversation"]["title"] == "turn off the lights"
    assert tree["conversation"]["active_leaf_id"] == tree["messages"][1]["id"]


def test_anything_else_is_left_for_the_model(app: TestClient, ha: FakeHA) -> None:
    connect(app)
    ha.agents_known = {"homeassistant"}  # an older Home Assistant's agent name
    assert app.post("/api/home/assist", json={"text": "write me a poem"}).json()["handled"] is False
    assert app.post("/api/home/assist", json={"text": "light please"}).json()["handled"] is True
    app.put("/api/home/prefs", json={"route_chat": False})
    assert app.post("/api/home/assist", json={"text": "light please"}).json()["handled"] is False


def test_assist_without_home_assistant_never_blocks_chat(app: TestClient) -> None:
    assert (
        app.post("/api/home/assist", json={"text": "turn off the lights"}).json()["handled"]
        is False
    )
