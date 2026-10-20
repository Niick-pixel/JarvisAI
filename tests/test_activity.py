"""Total transparency: anything running in the background shows in the HUD with what it is doing,
and a model load shows its stage and an honest estimate."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from server.hud import activity, telemetry
from server.main import create_app
from server.models.knowledge import IndexProgress
from server.providers import loadtimes
from server.settings import Settings


def test_a_load_reads_its_stage_from_the_log() -> None:
    log = "llama_model_loader: loaded meta\nload_tensors: offloaded 33/33 layers to GPU\n"
    assert loadtimes.stage(log) == "Moving layers onto the graphics card"
    assert loadtimes.stage(log + "srv  main: server is listening on 127.0.0.1") == "Ready"
    assert loadtimes.stage("") == ""


def test_the_estimate_is_last_times_load(tmp_path: Path) -> None:
    model = tmp_path / "m.gguf"
    model.write_bytes(b"x" * 1024)
    assert loadtimes.expected(tmp_path, model) > 0  # a guess from size, the first time
    loadtimes.record(tmp_path, model, 12.34)
    assert loadtimes.expected(tmp_path, model) == 12.3


def test_background_work_is_listed(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app):
        state = app.state.app
        assert activity.collect(state) == []
        state.indexer.progress["s1"] = IndexProgress(
            source_id="s1", state="chunking", files_total=4, files_done=1, detail="notes.md"
        )
        llama = state.llama
        if llama is not None:
            llama.status = llama.status.model_copy(
                update={
                    "loading": True,
                    "model_path": "/m/Qwen3-8B-Q4_K_M.gguf",
                    "load_stage": "Reading the model from disk",
                    "load_started_at": time.time() - 5,
                    "load_expected_s": 10.0,
                }
            )
        found = {a.kind: a for a in activity.collect(state)}
        assert found["index"].progress == 0.25 and found["index"].detail == "notes.md"
        if llama is not None:
            assert found["model"].label == "Loading Qwen3-8B-Q4_K_M.gguf"
            assert 0.4 < (found["model"].progress or 0) < 0.6
        sample = telemetry.sample(state)
        assert sample.activity and sample.model == ""  # loading is not serving
