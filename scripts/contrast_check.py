"""Verify every text colour clears 4.5:1 on every surface it can sit on, in both themes.

It reads web/src/design/tokens.json - the file the app itself turns into CSS variables - so the
check cannot pass a palette that is not on screen. Two kinds of surface are checked:

  * The solid ones: page, sidebar, cards, menus, your message bubble, code blocks.
  * The glow behind the composer, at its worst: all three colours stacked at the peak alpha the
    app ever paints them with (`halo_alpha`, also read by Halo.tsx). Real frames are fainter -
    the blobs are blurred and only partly overlap - so passing here means passing everywhere.
    Only body text (ink, ink-muted) is ever placed on the glow, so only that is required there.

If it fails, the fix is the palette or the glow's alpha, not the target.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "web" / "src" / "design" / "tokens.json"
TARGET = 4.5

SOLID = ["bg", "sidebar", "surface", "raised", "bubble", "code"]
ON_SOLID = ["ink", "ink-muted", "ink-faint", "accent", "danger", "success"]
ON_GLOW = ["ink", "ink-muted"]
# Filled controls: text colour on the fill colour.
FILLED = [("on-accent", "accent"), ("bg", "ink"), ("bg", "danger")]

Rgb = tuple[float, float, float]


def rgb(hex_colour: str) -> Rgb:
    value = int(hex_colour.lstrip("#"), 16)
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def luminance(colour: Rgb) -> float:
    def channel(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def over(top: Rgb, alpha: float, below: Rgb) -> Rgb:
    """CSS composites in sRGB space, which is what this does."""
    r, g, b = (t * alpha + u * (1 - alpha) for t, u in zip(top, below, strict=True))
    return (r, g, b)


def contrast(a: Rgb, b: Rgb) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_theme(name: str, palette: dict[str, Rgb], halo: dict[str, float]) -> list[str]:
    failures: list[str] = []
    glow = palette["bg"]
    for colour, alpha in halo.items():
        glow = over(palette[colour], alpha, glow)
    cases = [(text, surface, palette[surface]) for surface in SOLID for text in ON_SOLID]
    cases += [(text, "glow at its peak", glow) for text in ON_GLOW]
    cases += [(text, f"{fill} fill", palette[fill]) for text, fill in FILLED]
    print(name)
    for text, surface_name, surface in cases:
        ratio = contrast(palette[text], surface)
        ok = ratio >= TARGET
        print(f"  {'ok ' if ok else 'FAIL'} {text:>10} on {surface_name:<17} {ratio:5.2f}:1")
        if not ok:
            failures.append(f"{name}: {text} on {surface_name} is {ratio:.2f}:1")
    return failures


def main() -> int:
    tokens = json.loads(TOKENS.read_text())
    failures: list[str] = []
    for theme in ("light", "dark"):
        palette = {key: rgb(value) for key, value in tokens[theme].items()}
        failures += check_theme(theme, palette, tokens["halo_alpha"][theme])
    if failures:
        print("\ncontrast failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"\nall text clears {TARGET}:1 in both themes, including over the glow at its brightest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
