"""Your name and settings live in the database, so a cleared or private window cannot lose them."""

from fastapi.testclient import TestClient

from server.main import create_app
from server.settings import Settings


def test_prefs_merge_and_survive_a_restart(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/prefs").json() == {}
        client.put("/api/prefs", json={"name": "Nick", "mode": "dark"})
        assert client.put("/api/prefs", json={"mode": "light"}).json() == {
            "name": "Nick",
            "mode": "light",
        }
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/prefs").json()["name"] == "Nick"
