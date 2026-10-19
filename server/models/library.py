"""The models on this PC, as files: what they are, how big, and which one is serving."""

from __future__ import annotations

from pydantic import BaseModel


class LocalModel(BaseModel):
    id: str
    display_name: str
    file_path: str
    size_bytes: int
    quant: str | None = None
    loaded: bool = False
    """llama-server is serving this file right now."""
    pinned: bool = False
    """You chose it; the automatic choice is off."""
    deletable: bool = True
    """False for a file outside the models folder (from config.toml): Jarvis never deletes it."""


class LocalModels(BaseModel):
    models: list[LocalModel]
    folder: str
    total_bytes: int
