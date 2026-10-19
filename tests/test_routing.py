"""Smart model routing: each message goes to the model best suited to it, and says why."""

from __future__ import annotations

from conftest import FakeProvider
from fastapi.testclient import TestClient

from server.chat import routing
from server.main import create_app
from server.models.hardware import ModelOption
from server.models.provider import ModelInfo
from server.providers.registry import ProviderRegistry
from server.settings import Settings

CODER = "fake:qwen2.5-coder-7b-q4_k_m"
GENERAL = "fake:llama-3.1-8b-q4_k_m"
SMALL = "fake:llama-3.2-1b-q4_k_m"


def info(model_id: str, ctx: int = 8192) -> ModelInfo:
    name = model_id.split(":", 1)[1]
    return ModelInfo(id=model_id, provider="fake", display_name=name, ctx_len_max=ctx)


def option(model_id: str, ctx: int = 8192) -> ModelOption:
    return ModelOption(model=info(model_id, ctx), status="fits", recommended_ctx_len=ctx, reason="")


class Several(FakeProvider):
    async def list_models(self) -> list[ModelInfo]:
        return [info(GENERAL), info(CODER), info(SMALL)]


def test_messages_are_sorted_by_what_they_ask() -> None:
    assert routing.classify("Why does this throw a KeyError?\n```py\nd['x']\n```") == "code"
    assert routing.classify("What is the probability of two sixes in a row?") == "reasoning"
    assert routing.classify("Write a short poem about the sea") == "creative"
    assert routing.classify("hi!") == "quick"
    assert routing.classify("word " * 2000) == "long"
    long_chat = (
        "Tell me about your favourite places to visit in the autumn and what to pack for them"
    )
    assert routing.classify(long_chat) == "general"


def test_each_kind_of_question_goes_to_the_model_built_for_it() -> None:
    pool = [option(GENERAL), option(CODER), option(SMALL, ctx=32768)]
    code = routing.pick(pool, "code", scores={}, previous=None)
    assert code.model_id == CODER and "coding model" in code.note
    assert routing.pick(pool, "long", scores={}, previous=None).model_id == SMALL
    assert routing.pick(pool, "quick", scores={}, previous=None).model_id == SMALL
    # Nothing special about it: the model already answering keeps answering, so nothing reloads.
    kept = routing.pick(pool, "general", scores={}, previous=CODER)
    assert kept.model_id == CODER and "already answering" in kept.note


def test_your_council_verdicts_outrank_the_rules() -> None:
    pool = [option(GENERAL), option(CODER)]
    scores = {GENERAL: (4, 5), CODER: (1, 5)}
    chosen = routing.pick(pool, "code", scores=scores, previous=None)
    assert chosen.model_id == GENERAL and "won 4 of 5 Council rounds" in chosen.note
    # Two rounds are an anecdote, not a record.
    assert routing.pick(pool, "code", scores={GENERAL: (2, 2)}, previous=None).model_id == CODER


def test_smart_mode_routes_a_chat_and_keeps_the_reason_on_the_answer(settings: Settings) -> None:
    app = create_app(settings)
    app.state.app.registry = ProviderRegistry([Several()])
    with TestClient(app) as client:
        client.put("/api/models/selected", json={"model_id": "smart"})
        cid = client.post("/api/conversations", json={"title": "New conversation"}).json()["id"]
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"conversation_id": cid, "content": "my python script raises a traceback"},
        ) as response:
            b"".join(response.iter_bytes())
        answer = client.get(f"/api/conversations/{cid}").json()["messages"][-1]
        assert answer["model_id"] == CODER
        assert answer["route_note"].startswith("A coding question, so a coding model")

        # Pick a model yourself and the router steps aside: no note, no second-guessing.
        client.put("/api/models/selected", json={"model_id": GENERAL})
        with client.stream(
            "POST", "/api/chat/stream", json={"conversation_id": cid, "content": "and in rust?"}
        ) as response:
            b"".join(response.iter_bytes())
        answer = client.get(f"/api/conversations/{cid}").json()["messages"][-1]
        assert answer["model_id"] == GENERAL and answer["route_note"] is None
