"""Screen frames are scaled down before they are encoded - a 4K screen goes to a vision model at a
size it can read and a phone-sized preview at a size the page can refresh every second - and the
colours survive the trip from the OS's BGRA."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from server import screen
from server.main import create_app
from server.settings import Settings


def test_a_4k_frame_shrinks_with_its_colours_intact() -> None:
    bgra = np.zeros((2160, 3840, 4), np.uint8)
    bgra[..., 0], bgra[..., 1], bgra[..., 2] = 10, 120, 200  # blue, green, red
    rgb = screen._shrink(bgra, screen.FULL)
    assert max(rgb.shape[:2]) <= screen.FULL
    assert tuple(rgb[0, 0]) == (200, 120, 10)


def test_a_small_frame_is_left_alone() -> None:
    bgra = np.zeros((600, 800, 4), np.uint8)
    assert screen._shrink(bgra, screen.FULL).shape == (600, 800, 3)


def test_the_preview_is_never_stored(settings: Settings, monkeypatch) -> None:
    monkeypatch.setattr(screen, "grab_png", lambda longest=screen.FULL: b"\x89PNG fake")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/screen/frame?size=240")
        assert response.status_code == 200 and response.content == b"\x89PNG fake"
        assert response.headers["cache-control"] == "no-store"
    assert not (settings.paths.data_dir / "attachments").exists()
