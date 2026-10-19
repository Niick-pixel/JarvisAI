"""Settings > Data: each kind clears on its own, and "everything" leaves a fresh install behind -
with the downloaded models kept, because they cost gigabytes to fetch again."""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import create_app
from server.settings import Settings


def kinds(client: TestClient) -> dict[str, dict]:
    return {k["kind"]: k for k in client.get("/api/data").json()}


def test_clearing_chats_leaves_memory_and_models(settings: Settings) -> None:
    model = settings.paths.models_dir / "Tiny-Q4_K_M.gguf"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_bytes(b"x" * 100)
    with TestClient(create_app(settings)) as client:
        client.post("/api/conversations", json={"title": "a"})
        client.post("/api/memory", json={"content": "The user likes ES futures."})
        before = kinds(client)
        assert before["chats"]["count"] == 1 and before["memory"]["count"] == 1
        assert before["models"]["bytes"] >= 100

        after = {
            k["kind"]: k for k in client.post("/api/data/clear", json={"kind": "chats"}).json()
        }
        assert after["chats"]["count"] == 0
        assert after["memory"]["count"] == 1


def test_everything_resets_but_keeps_models(settings: Settings) -> None:
    model = settings.paths.models_dir / "Tiny-Q4_K_M.gguf"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_bytes(b"x" * 100)
    with TestClient(create_app(settings)) as client:
        client.post("/api/conversations", json={"title": "a"})
        client.post("/api/memory", json={"content": "The user likes ES futures."})
        client.post(
            "/api/agents/jobs",
            json={"name": "Notes", "cron": "0 9 * * 1-5", "prompt": "summarise", "tools": []},
        )
        after = {
            k["kind"]: k for k in client.post("/api/data/clear", json={"kind": "everything"}).json()
        }
        assert after["chats"]["count"] == 0 and after["memory"]["count"] == 0
        assert client.get("/api/agents/jobs").json() == []
        assert model.is_file()

        client.post("/api/data/clear", json={"kind": "models"})
        assert not model.exists()
