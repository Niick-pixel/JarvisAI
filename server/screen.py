"""A screenshot of the primary display, as PNG bytes, for a model that can see.

mss talks to the OS directly (GDI on Windows) and writes PNG itself, so this needs neither
Pillow nor a browser permission. It captures exactly what is on screen at that moment and nothing
else - no recording, no history.
"""

from __future__ import annotations


class NoScreen(RuntimeError):
    """There is no display to capture (a server without one, a locked session)."""


def grab_png() -> bytes:
    try:
        import mss
        import mss.tools
    except ImportError as exc:  # pragma: no cover - mss is a core dependency
        raise NoScreen("Screen capture is not available in this build.") from exc
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            png = mss.tools.to_png(shot.rgb, shot.size)
    except Exception as exc:  # noqa: BLE001 - every OS failure means the same thing here
        raise NoScreen(f"Could not capture the screen: {exc}") from exc
    if not png:
        raise NoScreen("The screen capture came back empty.")
    return png
