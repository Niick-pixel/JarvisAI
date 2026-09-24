"""Where things live: in a source checkout, and inside the packaged desktop app.

Two roots, because they answer different questions. The *resource* root holds what ships with the
app - the built frontend, the migrations, the model catalogue - and inside a PyInstaller bundle
that is the unpacked `_internal` folder, not the source tree. The *user* root holds what belongs
to you - the database, your memory, downloaded models - and an installed app must not keep that
next to its own executable, which may be read-only and is replaced on every update.

In a checkout both roots are the working directory, exactly as before, so nothing about
`make dev` changes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Jarvis"
SOURCE_ROOT = Path(__file__).resolve().parent.parent


def frozen() -> bool:
    """True inside the packaged app."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) if frozen() and bundle else SOURCE_ROOT


def resource(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def user_root() -> Path:
    """`JARVIS_HOME` wins, so a portable install or a test can put everything in one folder."""
    override = os.environ.get("JARVIS_HOME")
    if override:
        return Path(override)
    if not frozen():
        return Path(".")
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "jarvis"


def user_path(name: str) -> Path:
    return user_root() / name


def config_path() -> Path:
    """Beside your data in the app; at the repo root in a checkout, where it has always been."""
    if frozen() or os.environ.get("JARVIS_HOME"):
        return user_root() / "config.toml"
    return SOURCE_ROOT / "config.toml"


def bundled_llama_server() -> Path | None:
    """The llama.cpp build shipped inside the desktop app, if this is one and it has it."""
    name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    candidate = resource("llama", name)
    return candidate if frozen() and candidate.is_file() else None
