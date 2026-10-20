"""The mini widget: while Jarvis is minimised, a small always-on-top tile in the corner of the
screen with the same gauge as the HUD bubble - so a model loading or an answer running is never
invisible. Clicking it brings Jarvis back. Restoring Jarvis puts the tile away.

A second pywebview window on the same server (`/?widget=1`). Anything that goes wrong here is
logged and skipped: the widget is a convenience, and must never stop the main window opening.
"""

from __future__ import annotations

import logging
from typing import Any

SIZE = 128
MARGIN = 24
BACKGROUND = "#16181D"


class WidgetBridge:
    """What the tile's page may call. The windows are private so pywebview does not walk them."""

    def __init__(self) -> None:
        self._main: Any = None
        self._tile: Any = None

    def _attach(self, main: Any, tile: Any) -> None:
        self._main, self._tile = main, tile

    def restore_main(self) -> None:
        if self._tile is not None:
            self._tile.hide()
        if self._main is not None:
            self._main.restore()
            self._main.show()


def _corner() -> tuple[int | None, int | None]:
    """Bottom-right of the primary screen, above the taskbar; None lets the OS place it."""
    try:
        import webview

        screen = webview.screens[0]
        return screen.width - SIZE - MARGIN, screen.height - SIZE - MARGIN - 48
    except Exception:  # noqa: BLE001 - no screen info yet: let the OS decide
        return None, None


def attach(main: Any, url: str) -> None:
    try:
        import webview

        bridge = WidgetBridge()
        x, y = _corner()
        tile = webview.create_window(
            "Jarvis activity",
            f"{url}/?widget=1",
            width=SIZE,
            height=SIZE,
            x=x,
            y=y,
            frameless=True,
            easy_drag=True,
            on_top=True,
            resizable=False,
            hidden=True,
            focus=False,
            background_color=BACKGROUND,
            js_api=bridge,
        )
        if tile is None:
            return
        bridge._attach(main, tile)  # noqa: SLF001 - private so pywebview does not expose it
        main.events.minimized += tile.show
        main.events.restored += tile.hide
        main.events.closed += tile.destroy
    except Exception:  # noqa: BLE001 - see the module docstring
        logging.exception("the mini widget could not be set up; carrying on without it")
