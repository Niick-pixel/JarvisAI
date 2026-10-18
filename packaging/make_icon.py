"""Render packaging/jarvis.ico: the helm - a white sphere with one red lens in a ring with six
handles - on a dark tile. The same shapes as web/src/brand/Orb.tsx, in the same 0-100 units.

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
TILE_TOP, TILE_BOTTOM = np.array([0x22, 0x2B, 0x40]), np.array([0x0C, 0x10, 0x18])
WHITE, DARK, BEZEL = (
    np.array([0xF4, 0xF6, 0xF9]),
    np.array([0x2A, 0x2E, 0x36]),
    np.array([0x1C, 0x1F, 0x25]),
)
LENS_HOT, LENS_MID, LENS_EDGE = (
    np.array([0xFF, 0x6B, 0x5E]),
    np.array([0xE0, 0x20, 0x1B]),
    np.array([0x7A, 0x0A, 0x0A]),
)
HANDLES = (30, 90, 150, 210, 270, 330)
MARK_SCALE = 0.86
"""How much of the tile the mark fills."""


def _rounded_box(
    x: np.ndarray, y: np.ndarray, x0: float, y0: float, x1: float, y1: float, r: float
) -> np.ndarray:
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.maximum(np.abs(x - cx) - hx, 0), np.maximum(np.abs(y - cy) - hy, 0)
    return np.hypot(qx, qy) <= r


def _mix(t: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a * (1 - t)[..., None] + b * t[..., None]


def render(size: int) -> np.ndarray:
    n = size * SUPERSAMPLE
    ty, tx = (np.mgrid[0:n, 0:n] + 0.5) / n * 100  # tile units, 0-100
    x, y = (tx - 50) / MARK_SCALE + 50, (ty - 50) / MARK_SCALE + 50  # mark units

    def paint(mask: np.ndarray, colour: np.ndarray, alpha: float = 1.0) -> None:
        nonlocal rgb
        a = mask.astype(float) * alpha
        rgb = (
            rgb * (1 - a)[..., None]
            + (colour if colour.ndim == 3 else colour[None, None]) * a[..., None]
        )

    tile = _rounded_box(tx, ty, 0, 0, 100, 100, 22)
    # The lens lights the tile a little around it.
    glow = np.clip(0.30 - np.hypot(x - 50, y - 52) / 160, 0, 1)
    rgb = _mix(glow, _mix(ty / 100, TILE_TOP, TILE_BOTTOM), np.array([0xFF, 0x2A, 0x1F]))

    radius = np.hypot(x - 50, y - 50)
    paint(np.abs(radius - 38) <= 3.75, WHITE)
    for deg in HANDLES:
        a = np.radians(-deg)
        rx = (x - 50) * np.cos(a) - (y - 50) * np.sin(a) + 50
        ry = (x - 50) * np.sin(a) + (y - 50) * np.cos(a) + 50
        paint(_rounded_box(rx, ry, 84, 45, 99, 55, 5), WHITE)
        paint(_rounded_box(rx, ry, 84, 45.6, 89, 54.4, 1.5), DARK)

    shell = ((x - 50) / 26) ** 2 + ((y - 51) / 28) ** 2 <= 1
    light = np.clip(np.hypot(x - 40, y - 34) / 48, 0, 1) ** 1.6
    paint(shell, _mix(light, WHITE + 11, np.array([0xBF, 0xC5, 0xCF])).clip(0, 255))
    seam = (np.abs(x - 50) <= 1.2) & (((y >= 23.5) & (y <= 35)) | ((y >= 68) & (y <= 78.5)))
    paint(seam, DARK)
    paint(_rounded_box(x, y, 37, 32, 47, 34.6, 1.3), DARK, 0.75)

    lens_r = np.hypot(x - 50, y - 52)
    paint(lens_r <= 12, BEZEL)
    t = np.clip(np.hypot(x - 47, y - 49) / 11, 0, 1)
    lens = np.where(
        (t < 0.55)[..., None],
        _mix(t / 0.55, LENS_HOT, LENS_MID),
        _mix((t - 0.55) / 0.45, LENS_MID, LENS_EDGE),
    )
    paint(lens_r <= 8.8, lens)
    paint(np.hypot(x - 46.8, y - 48.8) <= 2.3, np.array([255, 255, 255]), 0.8)

    rgba = np.concatenate([rgb, (tile * 255)[..., None]], axis=-1)
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
