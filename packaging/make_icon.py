"""Pack packaging/icon/jarvis-<size>.png into packaging/jarvis.ico, plus a 256 px PNG beside it.

The frames are rendered from the logo, web/src/brand/jarvis.svg, by scripts/render_icon.mjs and
committed; this only packs them, so the Windows build needs no browser and no image library.
An ICO is a small directory followed by the PNGs themselves.
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

SIZES = (16, 24, 32, 48, 64, 128, 256)
HERE = Path(__file__).resolve().parent


def ico(images: list[bytes]) -> bytes:
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, data in zip(SIZES, images, strict=True):
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO directory
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    return struct.pack("<HHH", 0, 1, len(images)) + entries + blobs


def main() -> None:
    frames = [(HERE / "icon" / f"jarvis-{size}.png").read_bytes() for size in SIZES]
    target = HERE / "jarvis.ico"
    target.write_bytes(ico(frames))
    shutil.copyfile(HERE / "icon" / "jarvis-256.png", HERE / "jarvis-256.png")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
