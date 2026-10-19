"""The primary display, as PNG bytes, for a model that can see - once, or live while you share.

mss talks to the OS directly (GDI on Windows) and writes PNG itself, so this needs neither
Pillow nor a browser permission. Frames are scaled down with numpy before encoding: a model sees
a 4K screen at a fraction of that anyway, and a 1600 px frame is a faster answer and a smaller
file. Nothing is kept unless it goes with a message - no recording, no history.
"""

from __future__ import annotations

import numpy as np

FULL = 1600
"""The longest side of a frame sent with a message: small text stays legible to a vision model."""
PREVIEW = 480
"""The longest side of the live thumbnail above the composer."""


class NoScreen(RuntimeError):
    """There is no display to capture (a server without one, a locked session)."""


def _shrink(bgra: np.ndarray, longest: int) -> np.ndarray:
    """Average whole blocks of pixels: sharper than skipping pixels, and needs no image library."""
    height, width = bgra.shape[:2]
    step = max(1, -(-max(height, width) // longest))  # ceiling division
    if step == 1:
        return bgra[:, :, 2::-1]
    h, w = height - height % step, width - width % step
    blocks = bgra[:h, :w, :3].reshape(h // step, step, w // step, step, 3)
    return blocks.mean(axis=(1, 3)).astype(np.uint8)[:, :, ::-1]


def grab_png(longest: int = FULL) -> bytes:
    try:
        import mss
        import mss.tools
    except ImportError as exc:  # pragma: no cover - mss is a core dependency
        raise NoScreen("Screen capture is not available in this build.") from exc
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            pixels = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
            rgb = np.ascontiguousarray(_shrink(pixels, longest))
            png = mss.tools.to_png(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]))
    except Exception as exc:  # noqa: BLE001 - every OS failure means the same thing here
        raise NoScreen(f"Could not capture the screen: {exc}") from exc
    if not png:
        raise NoScreen("The screen capture came back empty.")
    return png
