"""A model bigger than the card must not be forced onto it: llama.cpp fits it itself, and only
when the layer count is left unset (its fit step aborts if -ngl is given)."""

from __future__ import annotations

import pytest

from server.providers import launch_args

NEW = "-fit,   --fit [on|off]   whether to adjust unset arguments to fit in device memory"
OLD = "-ngl, --gpu-layers N   number of layers to store in VRAM"


@pytest.fixture(autouse=True)
def fresh_help() -> None:
    launch_args._help_text.cache_clear()


def help_is(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(launch_args, "_help_text", lambda binary: text)


def test_a_current_build_fits_the_model_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    help_is(monkeypatch, NEW)
    argv = launch_args.gpu_args("llama-server", "gpt-oss-20b-mxfp4.gguf", has_gpu=True)
    assert argv == ["--fit", "on"]
    assert "-ngl" not in argv


def test_an_older_build_keeps_moe_experts_on_the_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    help_is(monkeypatch, OLD)
    assert launch_args.gpu_args("x", "Qwen3-30B-A3B-Q4_K_M.gguf", has_gpu=True) == [
        "-ngl",
        "999",
        "--n-cpu-moe",
        "999",
    ]
    assert launch_args.gpu_args("x", "Qwen3-8B-Q4_K_M.gguf", has_gpu=True) == ["-ngl", "999"]


def test_no_gpu_no_gpu_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    help_is(monkeypatch, NEW)
    assert launch_args.gpu_args("x", "Qwen3-8B-Q4_K_M.gguf", has_gpu=False) == []
