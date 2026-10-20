"""How long loading a model takes, and where a load has got to - so the app can show a real bar
instead of a frozen-looking window while gigabytes move from disk to the graphics card.

The stage comes from llama-server's own log lines. The estimate is how long this exact file took
last time on this PC; the first time, a guess from its size at an ordinary SSD's pace.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

FILE = "load_times.json"
FIRST_GUESS_MB_S = 600.0
OVERHEAD_S = 4.0

STAGES = (
    # Later stages first: the log holds all of them by the end, and the newest wins.
    ("HTTP server is listening", "Ready"),
    ("server is listening", "Ready"),
    ("warming up", "Warming up"),
    ("llama_kv_cache", "Making room for the conversation"),
    ("llama_context", "Making room for the conversation"),
    ("offloaded", "Moving layers onto the graphics card"),
    ("load_tensors", "Reading the model from disk"),
    ("params_fit", "Measuring free memory"),
    ("llama_model_loader", "Opening the model file"),
)


def stage(log_text: str) -> str:
    low = log_text.lower()
    best, at = "", -1
    for needle, label in STAGES:
        index = low.rfind(needle.lower())
        if index > at:
            best, at = label, index
    return best


def _read(data_dir: Path) -> dict[str, float]:
    try:
        raw = json.loads((data_dir / FILE).read_text())
        return {str(k): float(v) for k, v in raw.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def expected(data_dir: Path, model: Path) -> float:
    known = _read(data_dir).get(model.name)
    if known:
        return known
    try:
        size_mb = model.stat().st_size / 1_048_576
    except OSError:
        return 0.0
    return round(size_mb / FIRST_GUESS_MB_S + OVERHEAD_S, 1)


def record(data_dir: Path, model: Path, seconds: float) -> None:
    times = _read(data_dir)
    times[model.name] = round(seconds, 1)
    with contextlib.suppress(OSError):
        (data_dir / FILE).write_text(json.dumps(times))
