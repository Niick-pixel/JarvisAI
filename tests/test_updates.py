"""The updater: it believes the release's checksum, not the download, and never goes backwards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from server.settings import load_settings
from server.updates import install, updater
from server.updates.updater import Updater, newer, parse_version

INSTALLER = b"MZ pretend this is JarvisSetup.exe" * 1000
FEED = "https://example.invalid/latest.json"
URL = "https://example.invalid/JarvisSetup.exe"


def feed(version: str, sha256: str) -> dict[str, object]:
    return {
        "version": version,
        "notes": "Better window.",
        "installer": {"url": URL, "sha256": sha256, "size": len(INSTALLER)},
    }


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Answers the feed and the installer from memory, through httpx's own mock transport."""
    manifest: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == FEED:
            return httpx.Response(200, json=manifest)
        if str(request.url) == URL:
            return httpx.Response(200, content=INSTALLER)
        return httpx.Response(404)

    real = httpx.AsyncClient

    def client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", client)
    monkeypatch.setattr(install, "supported", lambda: True)
    return manifest


def make(tmp_path: Path) -> Updater:
    settings = load_settings(paths={"data_dir": tmp_path}, updates={"feed_url": FEED})
    return Updater(settings)


def test_versions_compare_as_numbers() -> None:
    assert parse_version("v0.10.2") == (0, 10, 2)
    assert newer("0.10.0", "0.9.9")
    assert not newer("v0.1.0", "0.1.0")
    assert not newer("0.0.9", "0.1.0")


async def test_older_or_same_release_is_up_to_date(tmp_path: Path, serve: dict) -> None:
    serve.update(feed(updater.VERSION, "0" * 64))
    status = await make(tmp_path).check()
    assert status.state == "up_to_date"


async def test_new_release_is_fetched_verified_and_ready(tmp_path: Path, serve: dict) -> None:
    serve.update(feed("99.0.0", hashlib.sha256(INSTALLER).hexdigest()))
    up = make(tmp_path)
    assert (await up.check(fetch=True)).state == "downloading"
    assert up._task is not None
    await up._task
    assert up.status.state == "ready", up.status.detail
    assert (tmp_path / "updates" / "JarvisSetup-99.0.0.exe").read_bytes() == INSTALLER


async def test_wrong_checksum_is_deleted_never_ready(tmp_path: Path, serve: dict) -> None:
    serve.update(feed("99.0.0", "f" * 64))
    up = make(tmp_path)
    await up.check(fetch=True)
    assert up._task is not None
    await up._task
    assert up.status.state == "failed"
    assert "checksum" in up.status.detail
    assert not list((tmp_path / "updates").glob("JarvisSetup-*"))


def test_auto_preference_survives_a_restart(tmp_path: Path) -> None:
    settings = load_settings(paths={"data_dir": tmp_path})
    Updater(settings).set_auto(False)
    assert Updater(settings).status.auto is False
    assert json.loads((tmp_path / "updates" / "prefs.json").read_text()) == {"auto": False}
