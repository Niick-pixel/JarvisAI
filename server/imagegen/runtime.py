"""stable-diffusion.cpp itself: which release asset suits this PC, and where its `sd` lives.

Chosen at install time from the project's latest GitHub release. On Windows the Vulkan build:
it runs on NVIDIA, AMD and Intel GPUs alike and needs no separate CUDA runtime; the CPU (AVX2)
build if there is no Vulkan one. The zip is checked against the sha256 GitHub publishes for it
when there is one, then unpacked into models/sdcpp.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from typing import Any

RELEASES = "https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest"
NAMES = ("sd.exe", "sd-cli.exe", "sd", "sd-cli")


def folder(models_dir: Path) -> Path:
    return models_dir / "sdcpp"


def find_binary(root: Path) -> Path | None:
    if not root.is_dir():
        return None
    for name in NAMES:
        for found in sorted(root.rglob(name)):
            if found.is_file():
                return found
    return None


def pick_asset(assets: list[dict[str, Any]], platform: str = sys.platform) -> dict[str, Any] | None:
    """The build for this OS, best backend first. Never the bare CUDA runtime zips."""
    zips = [
        a for a in assets if str(a.get("name", "")).endswith(".zip") and "cudart" not in a["name"]
    ]
    if platform == "win32":
        wanted = [r"win.*vulkan.*x64", r"win.*avx2.*x64", r"win.*x64"]
    elif platform == "darwin":
        wanted = [r"darwin.*arm64", r"macos.*arm64", r"darwin", r"macos"]
    else:
        wanted = [r"linux.*x86_64", r"ubuntu.*x86_64", r"linux"]
    for pattern in wanted:
        for asset in zips:
            if re.search(pattern, asset["name"], re.IGNORECASE):
                return asset
    return None


def digest_of(asset: dict[str, Any]) -> str:
    """GitHub's own `sha256:<hex>` for the file, when the release has one."""
    raw = str(asset.get("digest") or "")
    return raw.split(":", 1)[1] if raw.startswith("sha256:") else ""


def unpack(archive: Path, target: Path) -> Path | None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.namelist():
            resolved = (target / member).resolve()
            if not resolved.is_relative_to(target.resolve()):
                raise ValueError(f"refusing to unpack {member} outside {target}")
        zipped.extractall(target)
    binary = find_binary(target)
    if binary is not None and sys.platform != "win32":
        binary.chmod(0o755)
    return binary
