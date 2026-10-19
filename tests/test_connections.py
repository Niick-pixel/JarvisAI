"""Gmail and GitHub: credentials are checked before they are saved and never shown again; mail is
read as text (HTML stripped); GitHub answers are short lines an agent can act on."""

from __future__ import annotations

import asyncio
import json
from email.message import EmailMessage

import httpx
import pytest
from fastapi.testclient import TestClient

from server.connections import github as github_mod
from server.connections.github import GitHub, GitHubError
from server.connections.gmail import summarize
from server.main import create_app
from server.settings import Settings


def _mail(html: bool) -> bytes:
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = "bank@x.com", "me@x.com", "Statement"
    if html:
        message.set_content(
            "<html><style>p{}</style><p>Your <b>balance</b> is $12</p></html>", "html"
        )
    else:
        message.set_content("Your balance is $12.\n\n\nThanks")
    return message.as_bytes()


def test_a_message_is_read_as_text() -> None:
    assert "Your balance is $12" in summarize("7", _mail(html=False))
    full = summarize("7", _mail(html=True), snippet=False)
    assert "balance" in full and "<b>" not in full and "p{}" not in full
    assert full.startswith("[7]") and "From: bank@x.com" in full


def _github(handler) -> GitHub:
    return GitHub("t0ken", transport=httpx.MockTransport(handler))


def test_github_search_is_one_line_per_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer t0ken"
        item = {
            "repository_url": "https://api.github.com/repos/o/r",
            "number": 4,
            "state": "open",
            "title": "Crash on start",
            "user": {"login": "sam"},
            "updated_at": "2026-10-18T10:00:00Z",
            "pull_request": {},
        }
        return httpx.Response(200, json={"items": [item]})

    out = asyncio.run(_github(handler).search("is:pr"))
    assert out == "o/r#4 [PR, open] Crash on start - sam, updated 2026-10-18"


def test_a_refused_token_says_so() -> None:
    with pytest.raises(GitHubError, match="refused the token"):
        asyncio.run(_github(lambda r: httpx.Response(401)).login())


def test_connecting_shows_who_but_never_the_token(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def login(self: GitHub) -> str:
        return "octo"

    monkeypatch.setattr(github_mod.GitHub, "login", login)
    with TestClient(create_app(settings)) as client:
        status = client.put("/api/connections/github", json={"token": "ghp_secret"}).json()
        assert {"name": "github", "connected": True, "who": "octo"} in status
        assert "ghp_secret" not in json.dumps(client.get("/api/connections").json())
        client.delete("/api/connections/github")
        assert all(not s["connected"] for s in client.get("/api/connections").json())
