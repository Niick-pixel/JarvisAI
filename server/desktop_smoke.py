"""`Jarvis --smoke-test`: what CI runs against the built .exe, since no one clicks it there.

It checks the things a packaging mistake breaks while the app keeps politely reporting them -
the frontend bundled, the migrations found, the vector extension loadable. With
JARVIS_SMOKE_CHAT=1 it goes further: waits for the bundled llama-server to load a real model and
streams one reply through the whole pipeline, which is the only way to know the Windows launcher
works on Windows.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from collections.abc import Callable
from threading import Thread
from typing import Any

from server import paths

MODEL_WAIT_S = 240.0


def _request(url: str, body: dict[str, Any] | None = None, timeout: float = 5) -> bytes:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return bytes(response.read())


def _json(url: str, body: dict[str, Any] | None = None) -> Any:
    try:
        return json.loads(_request(url, body) or b"null")
    except (OSError, ValueError):
        return None


def _chat(url: str) -> tuple[int, str]:
    """(tokens received, why not) for one real turn through /api/chat/stream."""
    # "A backend answers" is the condition, not "we started one": a server already listening is
    # left alone by the launcher and is just as good for proving the pipeline.
    deadline = time.monotonic() + MODEL_WAIT_S
    while time.monotonic() < deadline:
        providers = _json(f"{url}/api/providers") or []
        if any(p.get("online") for p in providers):
            break
        time.sleep(1)
    else:
        launch = _json(f"{url}/api/providers/launch") or {}
        return 0, f"no backend came up: {launch.get('detail')}"
    conversation = _json(f"{url}/api/conversations", {"title": "smoke"}) or {}
    try:
        raw = _request(
            f"{url}/api/chat/stream",
            {
                "conversation_id": conversation.get("id"),
                "content": "Say hello.",
                "params": {"max_tokens": 16},
            },
            timeout=180,
        ).decode(errors="replace")
    except OSError as exc:
        return 0, f"stream failed: {exc}"
    tokens = raw.count("event: token")
    return tokens, "" if tokens else f"no tokens; stream began {raw[:200]!r}"


def smoke(url: str, stop: Callable[[], None], thread: Thread) -> int:
    try:
        frontend = _request(f"{url}/").decode(errors="replace")
    except OSError as exc:
        frontend = f"unreachable: {exc}"
    health = _json(f"{url}/api/health") or {}
    problems = [
        name
        for name, failed in (
            ("no health", not health),
            ("frontend not bundled", not frontend.lstrip().lower().startswith("<!doctype html")),
            ("sqlite-vec not loadable", not health.get("sqlite_vec")),
            ("migrations missing", not health.get("migrations_applied")),
        )
        if failed
    ]
    tokens = 0
    if os.environ.get("JARVIS_SMOKE_CHAT") == "1":
        tokens, why = _chat(url)
        if why:
            problems.append(why)
    report = {
        "health": health,
        "launch": _json(f"{url}/api/providers/launch"),
        "tokens_streamed": tokens,
        "user_root": str(paths.user_root().resolve()),
        "problems": problems,
    }
    print(json.dumps(report, indent=2))
    stop()
    if thread.is_alive():
        problems.append("server did not shut down")
    print("smoke test:", "ok" if not problems else "FAILED - " + "; ".join(problems))
    return 0 if not problems else 1
