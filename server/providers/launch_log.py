"""Reading llama-server's log: only this run's part of it, which the launcher appends to."""

from __future__ import annotations

from pathlib import Path

TAIL_LINES = 12


def recent(log_path: Path, start: int) -> str:
    """This run's log so far (its last 16 KB): where a model load has got to."""
    try:
        with log_path.open("rb") as handle:
            handle.seek(max(start, handle.seek(0, 2) - 16_384))
            return handle.read().decode(errors="replace")
    except OSError:
        return ""


def tail(log_path: Path, start: int) -> str:
    """This run's own last words, which are almost always the actual explanation."""
    try:
        with log_path.open("rb") as handle:
            handle.seek(start)
            lines = handle.read().decode(errors="replace").splitlines()
    except OSError:
        return f"see {log_path}"
    return " / ".join(line.strip() for line in lines[-TAIL_LINES:] if line.strip())[-600:]
