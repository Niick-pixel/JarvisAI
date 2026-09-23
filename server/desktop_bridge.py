"""What the window can ask the desktop for, through pywebview's JS bridge.

Only one thing today: a native folder picker, so adding a folder to Knowledge is "Choose folder"
and not "type a path". The page calls `window.pywebview.api.pick_folder()`; in a plain browser
that object does not exist and the page falls back to a text field.
"""

from __future__ import annotations

from typing import Any


class Bridge:
    """Every public attribute here becomes callable from the page, and pywebview walks public
    objects recursively to find them. The window is private for that reason: walking it calls
    its size, position and DOM getters, which on Windows wait for the UI thread - the thread
    doing the walk - and the app froze at "Not Responding" on its first launch."""

    def __init__(self) -> None:
        self._window: Any = None

    def _attach(self, window: Any) -> None:
        self._window = window

    def pick_folder(self) -> str | None:
        import webview

        if self._window is None:
            return None
        chosen = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not chosen:
            return None
        return str(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)
