"""Ctrl+Shift+Space, from anywhere on Windows: take a screenshot and ask Jarvis about it.

RegisterHotKey through ctypes - the OS's own global hotkey, not a keyboard hook - so nothing sees
your other keystrokes. Off Windows this does nothing; the "Look at my screen" button still works.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable

log = logging.getLogger("jarvis.hotkey")
MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x0002, 0x0004, 0x4000
VK_SPACE = 0x20
WM_HOTKEY = 0x0312
LABEL = "Ctrl+Shift+Space"


def listen(on_press: Callable[[], None]) -> bool:
    """Start listening on a background thread. False when there is no global hotkey here."""
    if sys.platform != "win32":
        return False

    def run() -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_SPACE):
            log.warning("%s is taken by another app; use the Look at my screen button", LABEL)
            return
        message = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY:
                    try:
                        on_press()
                    except Exception:  # noqa: BLE001 - one failed capture must not end the listener
                        log.exception("screen hotkey failed")
        finally:
            user32.UnregisterHotKey(None, 1)

    threading.Thread(target=run, name="jarvis-hotkey", daemon=True).start()
    return True
