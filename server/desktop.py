"""The desktop app: the same server, in its own window, started and stopped by double-click.

Nothing here is a second implementation of anything. It runs the FastAPI app on a free loopback
port in a background thread, waits until it answers, and opens a native window on it (Edge
WebView2 on Windows, which draws the shader like any browser). Closing the window shuts the server
down the ordinary way, which is what stops the llama-server it started.

Three things a packaged Windows app gets wrong unless told:
- A windowed PyInstaller build has no console, so sys.stdout is None, and the first log line
  uvicorn writes raises. Output goes to a log file in the user folder instead.
- A fixed port collides with whatever else you run. The port is picked at launch.
- A second double-click must not start a second server on the same database. It finds the
  running one and opens a window onto that instead.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from server import paths

TITLE = "Jarvis"
READY_TIMEOUT_S = 60.0
LOCK_NAME = "desktop.lock"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Jarvis")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="start the server, check it answers, print what it reports, shut down, exit",
    )
    args = parser.parse_args(argv)

    log_file = _route_output()
    if not args.smoke_test:
        existing = _running_instance()
        if existing:
            return _open_window(existing, server=None, log_file=log_file)

    port = _free_port()
    server, thread = _start_server(port)
    url = f"http://127.0.0.1:{port}"
    if not _wait_ready(url, thread):
        logging.error("the server did not come up; see %s", log_file)
        _stop(server, thread)
        return 1

    if args.smoke_test:
        from server.desktop_smoke import smoke

        return smoke(url, lambda: _stop(server, thread), thread)

    _write_lock(port)
    try:
        return _open_window(url, server=(server, thread), log_file=log_file)
    finally:
        _clear_lock()


def _route_output() -> Path:
    """Give a console-less process somewhere to write, before anything tries to."""
    log_dir = paths.user_path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "jarvis.log"
    if sys.stdout is None or sys.stderr is None or paths.frozen():
        stream = log_file.open("a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    return log_file


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _start_server(port: int) -> tuple[Any, threading.Thread]:
    import uvicorn

    from server.main import create_app
    from server.settings import load_settings

    # Loopback, always: the desktop app has no reason to be reachable from anywhere else, and
    # overriding here means a config.toml edited for `make dev` cannot change that.
    settings = load_settings(server={"host": "127.0.0.1", "port": port})
    config = uvicorn.Config(
        create_app(settings), host="127.0.0.1", port=port, log_config=None, access_log=False
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="jarvis-server", daemon=True)
    thread.start()
    return server, thread


def _wait_ready(url: str, thread: threading.Thread) -> bool:
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline and thread.is_alive():
        if _get(f"{url}/api/health") is not None:
            return True
        time.sleep(0.2)
    return False


def _get(url: str) -> Any | None:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read() or b"null")
    except (OSError, ValueError):
        return None


def _stop(server: Any, thread: threading.Thread) -> None:
    """The ordinary shutdown path, so the lifespan stops llama-server and the scheduler."""
    server.should_exit = True
    thread.join(timeout=30)


def _open_window(url: str, *, server: tuple[Any, threading.Thread] | None, log_file: Path) -> int:
    try:
        import webview
    except ImportError:
        logging.error("pywebview is not installed; opening the default browser instead")
        return _browser_fallback(url, server)
    window = webview.create_window(TITLE, url, width=1400, height=900, min_size=(900, 600))
    if window is None:
        logging.error("pywebview returned no window; opening the default browser instead")
        return _browser_fallback(url, server)
    if server is not None:
        window.events.closed += lambda: _stop(*server)
    try:
        webview.start()
    except Exception:  # noqa: BLE001 - no WebView2 runtime, no GUI backend: say so, degrade
        logging.exception("could not open a native window; opening the default browser instead")
        return _browser_fallback(url, server)
    return 0


def _browser_fallback(url: str, server: tuple[Any, threading.Thread] | None) -> int:
    import webbrowser

    webbrowser.open(url)
    if server is not None:
        with contextlib.suppress(KeyboardInterrupt):
            server[1].join()
    return 0


def _lock_path() -> Path:
    return paths.user_path(LOCK_NAME)


def _write_lock(port: int) -> None:
    _lock_path().write_text(json.dumps({"pid": os.getpid(), "port": port}))


def _clear_lock() -> None:
    _lock_path().unlink(missing_ok=True)


def _running_instance() -> str | None:
    """Another Jarvis window is already serving: open onto it instead of starting a second one."""
    try:
        lock = json.loads(_lock_path().read_text())
    except (OSError, ValueError):
        return None
    url = f"http://127.0.0.1:{int(lock.get('port', 0))}"
    return url if _get(f"{url}/api/health") is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
