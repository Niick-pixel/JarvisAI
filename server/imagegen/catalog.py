"""The image models offered for download. Turbo models: a picture in four steps, not fifty.

Like models.toml, files are resolved against Hugging Face when you press download - the real name,
size and sha256 - so an entry that no longer resolves shows as unavailable instead of failing.
"""

from __future__ import annotations

from typing import Any

IMAGE_MODELS: list[dict[str, Any]] = [
    {
        "key": "sd-turbo",
        "display_name": "SD Turbo",
        "hf_repo": "stabilityai/sd-turbo",
        "file_glob": "sd_turbo.safetensors",
        "width": 512,
        "height": 512,
        "steps": 4,
        "cfg": 1.0,
        "why": "Fast: a 512 px picture in a few seconds on a mid-range GPU. Smallest to download.",
        "license": "Stability AI Community License",
    },
    {
        "key": "sdxl-turbo",
        "display_name": "SDXL Turbo",
        "hf_repo": "stabilityai/sdxl-turbo",
        "file_glob": "sd_xl_turbo_1.0_fp16.safetensors",
        "width": 512,
        "height": 512,
        "steps": 4,
        "cfg": 1.0,
        "why": "Noticeably better pictures than SD Turbo, for about twice the time and VRAM.",
        "license": "Stability AI Community License",
    },
]


def entry(key: str) -> dict[str, Any] | None:
    return next((m for m in IMAGE_MODELS if m["key"] == key), None)
