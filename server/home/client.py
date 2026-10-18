"""Talking to Home Assistant's REST API: states, areas, service calls and Assist.

Everything goes to the address you gave, on your own network, with the token you created. Nothing
here touches Home Assistant's cloud. Commands typed or spoken in Jarvis go to Home Assistant's
built-in sentence matcher by name (`conversation.home_assistant`), never to whatever conversation
agent is its default - which may be a cloud language model you would not want your chat sent to.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
LOCAL_AGENTS = ("conversation.home_assistant", "homeassistant")
"""The built-in local agent's id: the first since 2024, the second before."""
# One template call names every entity's room; the REST API has no area endpoint of its own.
AREAS_TEMPLATE = (
    "{% set ns = namespace(out=[]) %}{% for s in states %}"
    "{% set ns.out = ns.out + [[s.entity_id, area_name(s.entity_id)]] %}"
    "{% endfor %}{{ ns.out | tojson }}"
)


class HomeError(RuntimeError):
    """Said to the person, so it explains the problem rather than naming an exception."""


class HomeAssistant:
    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, body: Any = None) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.request(
                    method, f"{self.url}{path}", headers=self._headers, json=body
                )
        except httpx.HTTPError as exc:
            raise HomeError(f"Couldn't reach Home Assistant at {self.url} ({exc}).") from exc
        if response.status_code == 401:
            raise HomeError("Home Assistant refused the token. Create a new long-lived token.")
        return response

    async def _json(self, method: str, path: str, body: Any = None) -> Any:
        response = await self._request(method, path, body)
        if response.status_code >= 400:
            raise HomeError(
                f"Home Assistant answered {response.status_code}: {response.text[:200]}"
            )
        return response.json()

    async def config(self) -> dict[str, Any]:
        result: dict[str, Any] = await self._json("GET", "/api/config")
        return result

    async def states(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = await self._json("GET", "/api/states")
        return result

    async def areas(self) -> dict[str, str]:
        """entity_id -> room name. Empty if templates are unavailable: rooms are a nicety."""
        response = await self._request("POST", "/api/template", {"template": AREAS_TEMPLATE})
        if response.status_code >= 400:
            return {}
        try:
            return {entity: area for entity, area in json.loads(response.text) if area}
        except (ValueError, TypeError):
            return {}

    async def call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        await self._json("POST", f"/api/services/{domain}/{service}", data)

    async def assist(self, text: str, language: str = "") -> tuple[bool, str]:
        """(handled, what Home Assistant said). Not handled means it was not a home command."""
        last = ""
        for agent in LOCAL_AGENTS:
            body: dict[str, Any] = {"text": text, "agent_id": agent}
            if language:
                body["language"] = language
            response = await self._request("POST", "/api/conversation/process", body)
            if response.status_code >= 400:
                last = response.text[:200]
                continue  # an older Home Assistant names its agent differently
            answer = response.json().get("response", {})
            speech = answer.get("speech", {}).get("plain", {}).get("speech", "")
            code = (answer.get("data") or {}).get("code", "")
            # "no_intent_match" is the only answer that means "not about the home". A command
            # that matched but named an unknown room is still Home Assistant's to answer.
            return answer.get("response_type") != "error" or code != "no_intent_match", speech
        raise HomeError(f"Home Assistant's Assist did not answer: {last}")
