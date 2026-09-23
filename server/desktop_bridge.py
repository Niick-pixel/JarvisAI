"""What the window can ask the desktop for, through pywebview's JS bridge.

Only one thing today: a native folder picker, so adding a folder to Knowledge is "Choose folder"
and not "type a path". The page calls `window.pywebview.api.pick_folder()`; in a plain browser
that object does not exist and the page falls back to a text field.
"""

from __future__ import annotations

from typing import Any


class Bridge:
    def __init__(self) -> None:
        self.window: Any = None

    def pick_folder(self) -> str | None:
        import webview

        if self.window is None:
            return None
        chosen = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if not chosen:
            return None
        return str(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)
