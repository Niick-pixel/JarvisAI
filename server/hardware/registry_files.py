"""Which file a catalogue entry means, whether you already have it, and recording that you do.

Moved out of scripts/models_cli.py so the CLI and the desktop app's download button are one
implementation. models.toml names a repo and a glob; the real filename, byte size and sha256 come
from the registry at the moment you ask, never from a table that goes stale.
"""

from __future__ import annotations

import functools
import sqlite3
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


@functools.lru_cache(maxsize=64)
def _resolve_cached(repo: str, glob: str) -> tuple[str | None, int | None, str | None]:
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(repo, files_metadata=True)
    except Exception:  # noqa: BLE001 - offline, rate limited, or the repo moved
        return None, None, None
    matches = [s for s in info.siblings or [] if fnmatch(s.rfilename, glob)]
    if not matches:
        return None, None, None
    # Several files can match a quant glob (split shards, imatrix variants): take the smallest
    # single file, which is the one that is actually a whole model at that quant.
    best = min(matches, key=lambda s: s.size or 0)
    lfs = getattr(best, "lfs", None)
    return best.rfilename, best.size, getattr(lfs, "sha256", None)


def resolve_file(entry: dict[str, Any]) -> tuple[str | None, int | None, str | None]:
    """(filename, size, sha256), or Nones when the registry cannot be reached. Never raises."""
    return _resolve_cached(entry["hf_repo"], entry["file_glob"])


def installed_file(entry: dict[str, Any], models_dir: Path) -> Path | None:
    """A file in models_dir that matches this entry's glob. Exact, not a fuzzy name comparison."""
    if not models_dir.is_dir():
        return None
    for path in sorted(models_dir.glob("*.gguf")):
        if fnmatch(path.name, entry["file_glob"]) or fnmatch(
            path.name.lower(), entry["file_glob"].lower()
        ):
            # The glob alone matches every model at that quant; the repo stem must be in the name.
            stem = entry["hf_repo"].split("/")[-1].lower().replace("-gguf", "")
            if stem.split("-")[0] in path.name.lower():
                return path
    return None


def register(
    conn: sqlite3.Connection, path: Path, entry: dict[str, Any], sha256: str | None, ctx_len: int
) -> None:
    """Record the file, so autostart can choose it and a rerun can verify the exact weights."""
    conn.execute(
        "INSERT OR REPLACE INTO models (id, provider, display_name, file_path, sha256, quant,"
        " size_bytes, ctx_len_max, supports_logprobs, supports_prefix, last_seen_at)"
        " VALUES (?,?,?,?,?,?,?,?,1,1,strftime('%s','now')*1000)",
        (
            f"llamacpp:{path.name}",
            "llamacpp",
            entry["display_name"],
            str(path),
            sha256 or "",
            entry.get("quant"),
            path.stat().st_size,
            ctx_len,
        ),
    )
