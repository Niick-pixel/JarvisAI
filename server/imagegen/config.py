"""[images] in config.toml: making pictures on this PC with stable-diffusion.cpp."""

from __future__ import annotations

from pydantic import BaseModel


class ImagesConfig(BaseModel):
    binary: str = ""
    """Your own stable-diffusion.cpp `sd` build. Empty means the one fetched from inside the app."""
    model: str = "sd-turbo"
    """A key from server/imagegen/catalog.py."""
    vae_tiling: bool = True
    """Decode in tiles: a little slower, and it fits next to a loaded chat model."""
    extra_args: list[str] = []
    timeout_s: float = 300.0
