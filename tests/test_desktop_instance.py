"""A second launch reopens the running Jarvis - unless it is an older one, which is stopped."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server import desktop
from server.version import VERSION


@pytest.fixture
def running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    (tmp_path / desktop.LOCK_NAME).write_text(json.dumps({"pid": 4242, "port": 5555}))
    state: dict[str, Any] = {"version": VERSION, "stopped": []}
    monkeypatch.setattr(desktop, "_get", lambda url: {"version": state["version"]})
    monkeypatch.setattr(desktop, "_stop_process", state["stopped"].append)
    return state


def test_the_same_version_is_reopened(running: dict[str, Any]) -> None:
    assert desktop._running_instance() == "http://127.0.0.1:5555"
    assert running["stopped"] == []


def test_an_older_version_left_running_is_stopped_not_reopened(running: dict[str, Any]) -> None:
    running["version"] = "0.1.0-older"
    assert desktop._running_instance() is None
    assert running["stopped"] == [4242]
