"""Where each file of an image model lives, and the stable-diffusion.cpp flag that loads it.

A single-file model (SD Turbo) is `-m <file>`. A model in parts gives each its own flag; the files
all live in models/images under their `save_as` names, so a part two models share is one file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

FLAGS = {
    "diffusion_model": "--diffusion-model",
    "vae": "--vae",
    "clip_l": "--clip_l",
    "t5xxl": "--t5xxl",
    "llm": "--llm",
}


def folder(models_dir: Path) -> Path:
    return models_dir / "images"


def files(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Every download this model needs: {hf_repo, file_glob, save_as}."""
    if "parts" in entry:
        return list(entry["parts"].values())
    return [
        {
            "hf_repo": entry["hf_repo"],
            "file_glob": entry["file_glob"],
            "save_as": entry["file_glob"],
        }
    ]


def path(models_dir: Path, spec: dict[str, Any]) -> Path:
    return folder(models_dir) / str(spec["save_as"])


def installed(models_dir: Path, entry: dict[str, Any]) -> bool:
    return all(path(models_dir, spec).is_file() for spec in files(entry))


def model_flags(models_dir: Path, entry: dict[str, Any]) -> list[str]:
    if "parts" not in entry:
        return ["-m", str(path(models_dir, files(entry)[0]))]
    flags: list[str] = []
    for role, spec in entry["parts"].items():
        flags += [FLAGS[role], str(path(models_dir, spec))]
    return flags
