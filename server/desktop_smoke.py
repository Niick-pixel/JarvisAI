"""`Jarvis --smoke-test`: what CI runs against the built .exe, since no one clicks it there.

It checks the things a packaging mistake breaks while the app keeps politely reporting them -
the frontend bundled, the migrations found, the vector extension loadable. With
JARVIS_SMOKE_CHAT=1 it goes further: waits for the bundled llama-server to load a real model and
streams one reply through the whole pipeline, which is the only way to know the Windows launcher
works on Windows. With JARVIS_SMOKE_VOICE=1 it downloads the voice pack the way the Settings
button does, has Piper say a sentence and Whisper transcribe it back, which proves both engines
survived the packaging.
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
VOICE_WAIT_S = 600.0
SPOKEN = "Hello from Jarvis."


def _request(
    url: str,
    body: dict[str, Any] | bytes | None = None,
    timeout: float = 5,
    content_type: str = "application/json",
) -> bytes:
    data = body if isinstance(body, bytes) else json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": content_type},
        method="POST" if data is not None else "GET",
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


def _voice(url: str) -> tuple[str, str]:
    """(what Whisper heard Piper say, why not)."""
    try:
        _request(f"{url}/api/voice/pack", b"", timeout=30)
    except OSError as exc:
        return "", f"voice pack would not start: {exc}"
    deadline = time.monotonic() + VOICE_WAIT_S
    progress: dict[str, Any] = {}
    while time.monotonic() < deadline:
        progress = _json(f"{url}/api/voice/pack") or {}
        if progress.get("state") not in ("downloading", "verifying"):
            break
        time.sleep(2)
    if progress.get("state") != "done":
        return "", f"voice pack did not finish: {progress}"
    try:
        wav = _request(f"{url}/api/voice/speak", {"text": SPOKEN}, timeout=120)
        heard = json.loads(
            _request(f"{url}/api/voice/transcribe", wav, timeout=180, content_type="audio/wav")
        ).get("text", "")
    except (OSError, ValueError) as exc:
        return "", f"speak/transcribe failed: {exc}"
    ok = "hello" in heard.lower()
    return heard, "" if ok else f"Whisper heard {heard!r}, not {SPOKEN!r}"


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
    heard = ""
    if os.environ.get("JARVIS_SMOKE_VOICE") == "1":
        heard, why = _voice(url)
        if why:
            problems.append(why)
    report = {
        "health": health,
        "launch": _json(f"{url}/api/providers/launch"),
        "tokens_streamed": tokens,
        "heard": heard,
        "user_root": str(paths.user_root().resolve()),
        "problems": problems,
    }
    print(json.dumps(report, indent=2))
    stop()
    if thread.is_alive():
        problems.append("server did not shut down")
    print("smoke test:", "ok" if not problems else "FAILED - " + "; ".join(problems))
    return 0 if not problems else 1
