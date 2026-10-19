"""How heavy a model is for *this* PC, said plainly before you download or switch to it.

Generating a word means reading every active weight once, so speed is set by memory bandwidth:
the part on the graphics card reads fast, the part spilled into system RAM reads about ten times
slower. These are ballpark figures, not benchmarks - they exist so a 20B model that would crawl
says so before it costs a 13 GB download, not after.

A mixture-of-experts model (Qwen3 30B-A3B, GPT-OSS 20B, DeepSeek Coder V2 Lite) only runs a few
billion of its weights per word. With the experts kept in system RAM it stays usable on a card
far smaller than the whole model, which is why those are the big models worth offering.
"""

from __future__ import annotations

from typing import Literal

from server.models.hardware import GpuInfo

Weight = Literal["light", "heavy", "too_heavy"]

GPU_GB_S = 350.0
"""A mid-range card's memory bandwidth, roughly; the RTX 3080 is 760, a 3060 is 360."""
RAM_GB_S = 40.0
"""Dual-channel DDR4/DDR5 as llama.cpp actually sees it."""
USABLE_WORDS_S = 8.0
"""Below this, reading along feels like waiting."""


def words_per_second(
    weights_mb: int, params_b: float, active_b: float | None, gpu: GpuInfo | None
) -> float:
    """A ballpark generation speed for this model on this machine."""
    active_mb = weights_mb * (active_b / params_b) if active_b else weights_mb
    vram = (gpu.vram_total_mb * 0.85) if gpu else 0.0
    if active_b and gpu and weights_mb > vram:
        # llama.cpp moves the experts to the CPU first, so most of what runs per word is in RAM.
        seconds = active_mb * 0.8 / 1024 / RAM_GB_S + active_mb * 0.2 / 1024 / GPU_GB_S
    else:
        on_gpu = min(active_mb, vram)
        seconds = on_gpu / 1024 / GPU_GB_S + (active_mb - on_gpu) / 1024 / RAM_GB_S
    # Tokens are about three quarters of a word.
    return round(0.75 / seconds, 1) if seconds > 0 else 0.0


def assess(
    *,
    display_name: str,
    weights_mb: int,
    params_b: float,
    active_b: float | None,
    gpu: GpuInfo | None,
    ram_mb: int | None,
) -> tuple[Weight, float, str]:
    """(weight, ballpark words/sec, the warning to show - empty when there is nothing to say)."""
    speed = words_per_second(weights_mb, params_b, active_b, gpu)
    gb = weights_mb / 1024
    room = (gpu.vram_total_mb if gpu else 0) + (ram_mb or 0) * 0.8
    if ram_mb is not None and weights_mb > room:
        return (
            "too_heavy",
            speed,
            (
                f"{display_name} needs about {gb:.0f} GB just to load, more than this PC's "
                "graphics card and free memory together. It will not run here."
            ),
        )
    if gpu is None:
        if speed >= USABLE_WORDS_S:
            return "light", speed, ""
        return (
            "heavy",
            speed,
            (
                f"No graphics card was found, so {display_name} would run on the processor "
                f"alone: expect roughly {max(speed, 0.5):.0f} words a second, and the PC busy "
                "while it answers."
            ),
        )
    if weights_mb <= gpu.vram_total_mb * 0.85:
        return "light", speed, ""
    where = f"your {gpu.name} ({gpu.vram_total_mb / 1024:.0f} GB)"
    if speed >= USABLE_WORDS_S:
        why = (
            f"It is a mixture-of-experts model - only {active_b:g}B of its {params_b:g}B run per "
            "word - so it should still manage"
            if active_b
            else "Part of it spills into system RAM, so expect"
        )
        return (
            "heavy",
            speed,
            (
                f"Heavy: about {gb:.0f} GB, bigger than {where}. {why} roughly {speed:.0f} words "
                "a second, but it takes most of your memory and the PC may feel sluggish while it "
                "answers."
            ),
        )
    return (
        "heavy",
        speed,
        (
            f"Very heavy: about {gb:.0f} GB on {where}. Expect roughly {max(speed, 0.5):.0f} "
            "words a second or less, long pauses before it starts, and the whole PC stuttering "
            "while it runs. A smaller model will feel far better."
        ),
    )
