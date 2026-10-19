"""The native window, and what happens when there cannot be one.

The first builds never showed a window at all: pywebview picks its Windows backend by importing
`webview.platforms.winforms` by name at runtime, PyInstaller cannot see a by-name import, so the
backend was missing from the .exe and every launch fell through to the browser - silently, which
is why nobody could tell. Now the spec bundles the backend, `--window-test` proves in CI that a
real window opens and renders the page, and a failure is a dialog that says what went wrong
instead of a browser tab that pretends nothing did.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from server import desktop_hotkey as hotkey
from server import paths

TITLE = "Jarvis"
WINDOW_TEST_TIMEOUT_S = 90.0
# The light theme's page colour, so the window never flashes white-then-grey on open.
BACKGROUND = "#F8F9FB"
# What "the app drew itself" means: React mounted something into #root.
RENDERED_JS = "document.getElementById('root') && document.getElementById('root').children.length"


def _gui() -> Literal["edgechromium"] | None:
    """Edge WebView2 on Windows, by name. Left to choose, pywebview falls back to the Internet
    Explorer engine when WebView2 is missing, which cannot run this page and shows a blank one."""
    return "edgechromium" if sys.platform == "win32" else None


def open_window(
    url: str, *, on_closed: Callable[[], None] | None, log_file: Path, quit_hook: list[Any]
) -> int:
    """Blocks until the window closes. `quit_hook` receives a callable that closes it from
    another thread - the update installer uses it to get out of its own way."""
    try:
        import webview

        from server.desktop_bridge import Bridge

        bridge = Bridge(url)
        window = webview.create_window(
            TITLE,
            url,
            width=1400,
            height=900,
            min_size=(900, 600),
            js_api=bridge,
            # Answers are meant to be selected and copied; pywebview disables that by default.
            text_select=True,
            background_color=BACKGROUND,
        )
        if window is None:
            raise RuntimeError("pywebview returned no window")
        bridge._attach(window)  # noqa: SLF001 - private so pywebview does not expose it
        quit_hook.append(window.destroy)
        if on_closed is not None:
            window.events.closed += on_closed
        hotkey.listen(lambda: _screen_to_chat(window, bridge))
        # Not private: pywebview's default is an incognito-style window whose storage is thrown
        # away on close, which made Jarvis forget your name and theme at every launch.
        webview.start(gui=_gui(), private_mode=False, storage_path=str(paths.user_path("webview")))
        return 0
    except Exception as exc:  # noqa: BLE001 - every way this fails ends at the same dialog
        logging.exception("could not open the Jarvis window")
        return _cannot_open(url, exc, log_file, on_closed)


def _screen_to_chat(window: Any, bridge: Any) -> None:
    """The hotkey: capture, bring Jarvis forward, and open a new chat with the screenshot."""
    attachment = bridge.capture_screen()
    window.restore()
    window.show()
    if attachment:
        window.evaluate_js(
            f"window.__jarvisScreen && window.__jarvisScreen({json.dumps(attachment)})"
        )


def _cannot_open(
    url: str, exc: BaseException, log_file: Path, on_closed: Callable[[], None] | None
) -> int:
    reason = str(exc) or type(exc).__name__
    webview2 = "webview2" in reason.lower() or "edge" in reason.lower()
    hint = (
        "Jarvis draws its window with Microsoft Edge WebView2, which this PC does not seem to "
        "have. Installing Jarvis again installs it, or get it from Microsoft (search "
        '"WebView2 Runtime").'
        if webview2
        else f"The details are in {log_file}."
    )
    message = (
        f"Jarvis could not open its window.\n\n{reason}\n\n{hint}\n\n"
        "Open Jarvis in your web browser for now?"
    )
    if _ask(message):
        import webbrowser

        webbrowser.open(url)
        logging.info("serving %s in the browser until the process is stopped", url)
        with contextlib.suppress(KeyboardInterrupt):
            threading.Event().wait()
    if on_closed is not None:
        on_closed()
    return 1


def _ask(message: str) -> bool:
    """A yes/no dialog with nothing but the OS: whatever broke the window may break any GUI
    library we would reach for here."""
    if sys.platform == "win32":
        import ctypes

        yes, flags = 6, 0x04 | 0x30  # IDYES; MB_YESNO | MB_ICONWARNING
        return bool(ctypes.windll.user32.MessageBoxW(None, message, TITLE, flags) == yes)
    print(message, file=sys.stderr)
    return False


def window_test(url: str) -> int:
    """`Jarvis --window-test`: open the real window on the real page, check React drew into it,
    close it. CI runs this on the built .exe, because the smoke test never opens a window and so
    passed for months while every user got a browser tab."""
    import webview

    result: dict[str, Any] = {"rendered": 0, "error": ""}
    window = webview.create_window(TITLE, url, width=1000, height=700, background_color=BACKGROUND)
    if window is None:
        logging.error("window test: pywebview returned no window")
        return 1

    def probe() -> None:
        try:
            for _ in range(int(WINDOW_TEST_TIMEOUT_S * 2)):
                result["rendered"] = int(window.evaluate_js(RENDERED_JS) or 0)
                if result["rendered"]:
                    break
                threading.Event().wait(0.5)
        except Exception as exc:  # noqa: BLE001 - reported below, not raised in a GUI thread
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            window.destroy()

    window.events.loaded += lambda: threading.Thread(target=probe, daemon=True).start()
    timer = threading.Timer(WINDOW_TEST_TIMEOUT_S + 30, window.destroy)
    timer.start()
    try:
        webview.start(gui=_gui())
    finally:
        timer.cancel()
    backend = getattr(webview, "guilib", None)
    logging.info(
        "window test: backend=%s rendered=%s error=%s",
        getattr(backend, "__name__", backend),
        result["rendered"],
        result["error"] or "none",
    )
    return 0 if result["rendered"] else 1
