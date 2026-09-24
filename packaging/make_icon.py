"""Render packaging/jarvis.ico: the app's four-point sparkle on its aurora gradient.

Generated rather than committed as a binary, so the icon is reviewable as code and needs no image
library - numpy for the pixels, zlib for PNG, and ICO is just a directory of PNGs.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np

SIZES = (16, 24, 32, 48, 64, 128, 256)
SUPERSAMPLE = 4
TOP, BOTTOM = np.array([0x5B, 0x8D, 0xEF]), np.array([0x9B, 0x6B, 0xF2])
GLOW = np.array([0xFF, 0xC4, 0x6B])


def render(size: int) -> np.ndarray:
    n = size * SUPERSAMPLE
    y, x = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    radius = np.hypot(x, y)
    # A rounded tile, not a circle: it reads as an app icon at 16px where a circle reads as a dot.
    corner = 0.42
    q = np.maximum(np.abs(x) - (1 - corner), 0), np.maximum(np.abs(y) - (1 - corner), 0)
    tile = (np.hypot(*q) <= corner * 0.98).astype(float)
    t = (y + 1) / 2
    colour = TOP * (1 - t)[..., None] + BOTTOM * t[..., None]
    colour = colour + (GLOW - colour) * np.clip(0.55 - radius, 0, 1)[..., None] * 0.6
    # The sparkle is an astroid, |x|^(2/3) + |y|^(2/3) <= r^(2/3): four concave points, like the
    # composer's mark, with no path rasteriser needed.
    star = (np.abs(x / 0.78) ** (2 / 3) + np.abs(y / 0.78) ** (2 / 3)) <= 1
    colour = np.where(star[..., None], np.array([255, 255, 255]), colour)
    rgba = np.concatenate([colour, (tile * 255)[..., None]], axis=-1)
    small = rgba.reshape(size, SUPERSAMPLE, size, SUPERSAMPLE, 4).mean(axis=(1, 3))
    return np.clip(small, 0, 255).astype(np.uint8)


def png(pixels: np.ndarray) -> bytes:
    height, width, _ = pixels.shape
    raw = b"".join(b"\x00" + pixels[row].tobytes() for row in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def ico(images: list[bytes]) -> bytes:
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, data in zip(SIZES, images, strict=True):
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO directory
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    return struct.pack("<HHH", 0, 1, len(images)) + entries + blobs


def main() -> None:
    target = Path(__file__).resolve().parent / "jarvis.ico"
    target.write_bytes(ico([png(render(size)) for size in SIZES]))
    (target.parent / "jarvis-256.png").write_bytes(png(render(256)))
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
