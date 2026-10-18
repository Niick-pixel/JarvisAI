"""What llama.cpp's /completion stream chunks mean: why it stopped, and how sure it was."""

from __future__ import annotations

import math
from typing import Any

from server.models.stream import Alternative


def stop_reason(chunk: dict[str, Any]) -> str:
    stop_type = chunk.get("stop_type")
    if stop_type in ("limit", "length"):
        return "length"
    if stop_type == "word":
        return "stop_word"  # one of the stop strings we passed: heavy thinking's </think>
    return "eos"


def probabilities(chunk: dict[str, Any]) -> tuple[float | None, list[Alternative] | None]:
    """Normalise the two shapes llama.cpp has shipped for `completion_probabilities`."""
    entries = chunk.get("completion_probabilities")
    if not entries:
        return None, None
    entry = entries[0]
    if "top_logprobs" in entry:
        alts = [
            Alternative(token=a.get("token", ""), logprob=float(a.get("logprob", 0.0)))
            for a in entry.get("top_logprobs", [])
        ]
        return _as_float(entry.get("logprob")), alts or None
    if "probs" in entry:
        alts = [
            Alternative(
                token=a.get("tok_str", ""),
                logprob=math.log(max(float(a.get("prob", 0.0)), 1e-12)),
            )
            for a in entry.get("probs", [])
        ]
        return (alts[0].logprob if alts else None), alts or None
    return None, None


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) else None
