"""The Sovereign HUD (BRIEF.md 4.10). A vanity metric, and satisfying, which is the point."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from server.models.hardware import GpuInfo


class Activity(BaseModel):
    """One thing happening in the background, as the activity panel lists it."""

    kind: Literal["model", "answer", "download", "image", "index", "update", "forecast", "agent"]
    label: str
    detail: str = ""
    progress: float | None = None
    """0-1 when it can be measured; None shows as working without a percentage."""
    seconds: int | None = None


class HudSample(BaseModel):
    gpu: GpuInfo | None = None
    """None on a machine with no NVIDIA GPU. Fields NVML withholds stay None - never invented."""
    ram_used_mb: int
    ram_total_mb: int
    tokens_per_second: float = 0.0
    active_runs: int = 0
    cpu_percent: float = 0.0
    model: str = ""
    """The model llama-server is serving, by file name; empty when none is loaded."""
    activity: list[Activity] = []


class LifetimeCounters(BaseModel):
    tokens_generated: float
    runs_completed: float
    cost_avoided_usd: float
    rate_per_million_usd: float
    """The assumed API price this comparison uses. Editable, and shown rather than magic."""
