"""The model manager: list the files, switch to one, delete one - never one outside the folder."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from server.db.connection import Database
from server.hardware import registry_files
from server.main import create_app
from server.settings import Settings


def add(db: Database, path: Path, name: str) -> None:
    path.write_bytes(b"GGUF" + b"\0" * 64)
    with db.session() as conn:
        registry_files.register(conn, path, {"display_name": name, "quant": "Q4_K_M"}, None, 4096)


def test_list_use_and_delete(settings: Settings, db: Database, tmp_path: Path) -> None:
    folder = settings.paths.models_dir
    folder.mkdir(parents=True, exist_ok=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    add(db, folder / "small.gguf", "Small")
    add(db, folder / "big.gguf", "Big")
    add(db, elsewhere / "mine.gguf", "Mine")

    with TestClient(create_app(settings)) as client:
        listed = client.get("/api/models/local").json()
        by_name = {m["display_name"]: m for m in listed["models"]}
        assert set(by_name) == {"Small", "Big", "Mine"} and not by_name["Mine"]["deletable"]

        used = client.post(f"/api/models/local/{by_name['Big']['id']}/use").json()
        assert [m["display_name"] for m in used["models"] if m["pinned"]] == ["Big"]

        left = client.delete(f"/api/models/local/{by_name['Big']['id']}").json()
        assert {m["display_name"] for m in left["models"]} == {"Small", "Mine"}
        assert not (folder / "big.gguf").exists()
        assert not any(m["pinned"] for m in left["models"])  # deleting the pinned one unpins

        refused = client.delete(f"/api/models/local/{by_name['Mine']['id']}")
        assert refused.status_code == 400 and (elsewhere / "mine.gguf").exists()
