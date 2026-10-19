"""GitHub with a personal access token: notifications, finding issues and pull requests, reading
one with its discussion, and - through the approval gate - commenting on it.

A fine-grained token can be limited to read-only and to chosen repositories; Settings says so.
"""

from __future__ import annotations

from typing import Any

import httpx

API = "https://api.github.com"
TIMEOUT = 20.0


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._transport = transport

    async def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(
            base_url=API, headers=self._headers, timeout=TIMEOUT, transport=self._transport
        ) as client:
            try:
                response = await client.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                raise GitHubError(f"Couldn't reach GitHub ({exc}).") from exc
        if response.status_code == 401:
            raise GitHubError("GitHub refused the token. It may have expired - reconnect it.")
        if response.status_code == 404:
            raise GitHubError("Not found, or the token cannot see it.")
        if response.status_code >= 400:
            raise GitHubError(f"GitHub said {response.status_code}: {response.text[:200]}")
        return response.json()

    async def login(self) -> str:
        return str((await self._call("GET", "/user"))["login"])

    async def notifications(self, limit: int = 20) -> str:
        items = await self._call("GET", "/notifications", params={"per_page": limit})
        lines = [
            f"{n['repository']['full_name']} | {n['subject']['type']}: {n['subject']['title']}"
            f" ({n['reason']}, {n['updated_at'][:10]})"
            for n in items
        ]
        return "\n".join(lines) or "No unread notifications."

    async def search(self, query: str, limit: int = 15) -> str:
        found = await self._call(
            "GET", "/search/issues", params={"q": query, "per_page": limit, "sort": "updated"}
        )
        lines = []
        for item in found.get("items", []):
            repo = item["repository_url"].removeprefix(f"{API}/repos/")
            kind = "PR" if "pull_request" in item else "issue"
            lines.append(
                f"{repo}#{item['number']} [{kind}, {item['state']}] {item['title']}"
                f" - {item['user']['login']}, updated {item['updated_at'][:10]}"
            )
        return "\n".join(lines) or "Nothing matched."

    async def read(self, repo: str, number: int) -> str:
        issue = await self._call("GET", f"/repos/{repo}/issues/{number}")
        comments = await self._call(
            "GET", f"/repos/{repo}/issues/{number}/comments", params={"per_page": 30}
        )
        head = (
            f"{repo}#{number}: {issue['title']} [{issue['state']}] by {issue['user']['login']}\n\n"
            f"{issue.get('body') or '(no description)'}"
        )
        thread = [
            f"--- {c['user']['login']} ({c['created_at'][:10]}):\n{c['body']}" for c in comments
        ]
        return "\n\n".join([head, *thread])

    async def comment(self, repo: str, number: int, body: str) -> str:
        made = await self._call(
            "POST", f"/repos/{repo}/issues/{number}/comments", json={"body": body}
        )
        return str(made.get("html_url", "Comment posted."))
