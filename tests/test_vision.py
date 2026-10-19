"""Images in chat: stored, linked to their message, sent to a model that can see in the shape each
backend expects - and never sent to one that cannot."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest
from conftest import FakeProvider
from fastapi.testclient import TestClient

from server import screen
from server.main import create_app
from server.models.provider import ModelInfo
from server.providers import launch_args
from server.providers.base import PromptMessage
from server.providers.llamacpp import chatml_prompt
from server.providers.openai_compat import _message
from server.providers.registry import ProviderRegistry
from server.settings import Settings

# The smallest valid PNG: one transparent pixel.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class Models(FakeProvider):
    """Two models on one backend: one that sees, one that does not."""

    def __init__(self, seeing: bool = True) -> None:
        super().__init__()
        self.seeing = seeing

    async def list_models(self) -> list[ModelInfo]:
        blind = ModelInfo(
            id="fake:text-8b", provider="fake", display_name="text-8b", ctx_len_max=8192
        )
        if not self.seeing:
            return [blind]
        eyes = ModelInfo(
            id="fake:eyes-4b",
            provider="fake",
            display_name="eyes-4b",
            ctx_len_max=8192,
            supports_vision=True,
        )
        return [blind, eyes]


def send(client: TestClient, cid: str, content: str, attachments: list[str]) -> dict[str, Any]:
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"conversation_id": cid, "content": content, "attachments": attachments},
    ) as response:
        raw = b"".join(response.iter_bytes()).decode()
        status = response.status_code
    return {"status": status, "raw": raw}


def test_an_image_reaches_a_model_that_can_see(settings: Settings) -> None:
    provider = Models()
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([provider])
    with TestClient(app) as client:
        client.put("/api/models/selected", json={"model_id": "fake:text-8b"})
        uploaded = client.post("/api/attachments", content=PNG).json()
        assert uploaded["mime"] == "image/png" and client.get(uploaded["url"]).content == PNG

        cid = client.post("/api/conversations", json={"title": "x"}).json()["id"]
        send(client, cid, "what is in this picture?", [uploaded["id"]])

        # You chose a model that cannot see, so this one turn went to one that can - and says so.
        messages = client.get(f"/api/conversations/{cid}").json()["messages"]
        question, answer = messages[-2], messages[-1]
        assert [a["id"] for a in question["attachments"]] == [uploaded["id"]]
        assert answer["model_id"] == "fake:eyes-4b"
        assert (
            answer["route_note"] == "This message has an image, so a model that can see: eyes-4b."
        )
        sent = [m for m in provider.prompts[-1] if m.images]
        assert sent[0].content.endswith("what is in this picture?")
        assert sent[0].images[0].startswith("data:image/png;base64,")


def test_no_seeing_model_means_a_clear_refusal(settings: Settings) -> None:
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([Models(seeing=False)])
    with TestClient(app) as client:
        image = client.post("/api/attachments", content=PNG).json()["id"]
        cid = client.post("/api/conversations", json={"title": "x"}).json()["id"]
        result = send(client, cid, "what is this?", [image])
        assert result["status"] == 400
        assert "no model that can see is running" in result["raw"]
        assert "choose_model" in result["raw"]


def test_only_real_images_are_accepted(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        refused = client.post("/api/attachments", content=b"MZ\x90\x00 not a picture")
        assert refused.status_code == 400 and "not a PNG" in refused.json()["message"]


def test_the_screen_is_captured_as_an_image(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    with TestClient(create_app(settings)) as client:
        monkeypatch.setattr(screen, "grab_png", lambda: PNG)
        shot = client.post("/api/screen/capture").json()
        assert shot["source"] == "screen" and shot["mime"] == "image/png"

        def nothing() -> bytes:
            raise screen.NoScreen("Could not capture the screen: no display")

        monkeypatch.setattr(screen, "grab_png", nothing)
        missing = client.post("/api/screen/capture")
        assert missing.status_code == 503 and "no display" in missing.json()["message"]


def test_each_backend_gets_images_its_own_way(settings: Settings, tmp_path: Path) -> None:
    url = "data:image/png;base64,AAAA"
    message = PromptMessage(role="user", content="what is this?", images=[url])
    # llama.cpp: a media marker per image in the text; the images ride beside the prompt.
    assert "<__media__>what is this?" in chatml_prompt([message])
    # OpenAI-compatible (LM Studio, Ollama): text and image parts.
    assert _message(message)["content"] == [
        {"type": "text", "text": "what is this?"},
        {"type": "image_url", "image_url": {"url": url}},
    ]
    assert _message(PromptMessage(role="user", content="hi")) == {"role": "user", "content": "hi"}
    # A vision model's projector, downloaded beside it, is loaded with it.
    model = tmp_path / "gemma-3-4b-it-Q4_K_M.gguf"
    model.write_bytes(b"x")
    assert "--mmproj" not in launch_args.command(settings, str(model), 4096)
    launch_args.mmproj_for(str(model)).write_bytes(b"x")
    argv = launch_args.command(settings, str(model), 4096)
    assert argv[argv.index("--mmproj") + 1] == str(tmp_path / "gemma-3-4b-it-Q4_K_M.mmproj")
