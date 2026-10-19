"""Code mode: the agent works in the project folder you chose - its instructions say so, writes
land there - and a folder that does not exist is refused before anything runs."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from server.chat.run import tool_instructions
from server.main import create_app
from server.settings import Settings


def test_the_instructions_name_the_project(tmp_path: Path) -> None:
    text = tool_instructions(["read_file", "write_file"], str(tmp_path))
    assert f"coding agent in the project folder {tmp_path}" in text
    assert "coding agent" not in tool_instructions(["read_file"])


def test_a_missing_project_folder_is_refused(settings: Settings, tmp_path: Path) -> None:
    with TestClient(create_app(settings)) as client:
        cid = client.post("/api/conversations", json={"title": "x"}).json()["id"]
        response = client.post(
            "/api/chat/agent",
            json={"conversation_id": cid, "content": "hi", "project": str(tmp_path / "nope")},
        )
        assert response.status_code == 400
        assert "not a folder" in response.json()["message"]


def test_the_project_is_the_workspace(settings: Settings, tmp_path: Path) -> None:
    from server.chat.agentic import ChatAgents

    with TestClient(create_app(settings)) as client:
        agents: ChatAgents = client.app.state.app.chat_agents  # type: ignore[attr-defined]
        job = agents._job(["write_file"], str(tmp_path))  # noqa: SLF001
        assert job.workspace == str(tmp_path)
        assert agents._job(["write_file"]).workspace.endswith("chat")  # noqa: SLF001
