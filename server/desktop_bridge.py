"""What the window can ask the desktop for, through pywebview's JS bridge.

A native folder picker, so adding a folder is "Choose folder" and not "type a path"; and a
screenshot that does not include Jarvis itself - the window steps aside for the capture. The page
calls `window.pywebview.api.<name>()`; in a plain browser that object does not exist and the page
falls back (a text field; the server-side capture).
"""

from __future__ import annotations

import sys
import time
from typing import Any

import httpx

from server import screen


class Bridge:
    """Every public attribute here becomes callable from the page, and pywebview walks public
    objects recursively to find them. The window is private for that reason: walking it calls
    its size, position and DOM getters, which on Windows wait for the UI thread - the thread
    doing the walk - and the app froze at "Not Responding" on its first launch."""

    def __init__(self, url: str = "") -> None:
        self._window: Any = None
        self._url = url

    def _attach(self, window: Any) -> None:
        self._window = window

    def capture_screen(self) -> dict[str, Any] | None:
        """Hide the window, capture the screen behind it, bring it back, store the image."""
        window = self._window
        if window is not None:
            window.hide()
            time.sleep(0.35)  # let the compositor actually take it off the screen
        try:
            png = screen.grab_png()
        except screen.NoScreen:
            return None
        finally:
            if window is not None:
                window.show()
        response = httpx.post(f"{self._url}/api/attachments", content=png, timeout=30.0)
        return response.json() if response.status_code == 200 else None

    def exclude_from_capture(self, on: bool) -> bool:
        """While you share your screen, leave Jarvis's own window out of every capture, so what
        it sees is the app behind it rather than itself. Windows 10 2004 and later.

        The window is found by its title rather than through pywebview's handle: reading the
        native handle from this thread waits on the UI thread, which is the freeze above."""
        if sys.platform != "win32":
            return False
        import ctypes

        from server.desktop_window import TITLE

        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, TITLE)
        if not hwnd:
            return False
        exclude, normal = 0x11, 0x0  # WDA_EXCLUDEFROMCAPTURE, WDA_NONE
        return bool(user32.SetWindowDisplayAffinity(hwnd, exclude if on else normal))

    def pick_folder(self) -> str | None:
        import webview

        if self._window is None:
            return None
        chosen = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not chosen:
            return None
        return str(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)
