"""Making pictures: the right stable-diffusion.cpp build for the PC, unpacked safely, run with the
model's own settings - and the picture lands in the chat as the answer."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.imagegen import catalog, parts, runtime
from server.imagegen.engine import ImageEngine
from server.main import create_app
from server.settings import Settings

ASSETS = [
    {"name": "sd-master-abc-bin-win-avx2-x64.zip"},
    {"name": "sd-master-abc-bin-win-vulkan-x64.zip", "digest": "sha256:" + "a" * 64},
    {"name": "cudart-sd-bin-win-cu12-x64.zip"},
    {"name": "sd-master-abc-bin-win-cuda12-x64.zip"},
    {"name": "sd-master-abc-bin-Linux-Ubuntu-24.04-x86_64.zip"},
    {"name": "sd-master-abc-bin-Darwin-macOS-15-arm64.zip"},
]

FAKE_SD = """
import sys
args = sys.argv[1:]
out = args[args.index("-o") + 1]
steps = int(args[args.index("--steps") + 1])
for step in range(1, steps + 1):
    print(f"  |=====>   | {step}/{steps} - 0.50s/it", flush=True)
png = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63646060f80f00010501019f4f9a8a0000000049454e44ae426082"
)
open(out, "wb").write(png)
"""


def test_the_build_for_this_pc_is_chosen() -> None:
    win = runtime.pick_asset(ASSETS, "win32")
    assert win is not None and "vulkan" in win["name"]  # runs on any GPU, no CUDA runtime needed
    assert runtime.digest_of(win) == "a" * 64
    linux = runtime.pick_asset(ASSETS, "linux")
    mac = runtime.pick_asset(ASSETS, "darwin")
    assert linux is not None and "Linux" in linux["name"]
    assert mac is not None and "arm64" in mac["name"]
    assert runtime.pick_asset([{"name": "cudart-sd-bin-win-cu12-x64.zip"}], "win32") is None


def test_unpacking_finds_sd_and_refuses_to_escape(tmp_path: Path) -> None:
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as z:
        z.writestr("bin/sd.exe", b"MZ")
    assert runtime.unpack(good, tmp_path / "out") == tmp_path / "out" / "bin" / "sd.exe"
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../../outside.txt", b"x")
    with pytest.raises(ValueError, match="outside"):
        runtime.unpack(evil, tmp_path / "out2")


def test_a_picture_becomes_the_answer(
    settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "fake_sd.py"
    script.write_text(FAKE_SD)
    sd = runtime.folder(settings.paths.models_dir) / "sd.exe"
    sd.parent.mkdir(parents=True)
    sd.write_bytes(b"MZ")
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/api/images/status").json()["ready"] is False  # no model yet
        engine: ImageEngine = app.state.app.images
        model = parts.path(
            settings.paths.models_dir, parts.files(catalog.entry("sd-turbo") or {})[0]
        )
        model.parent.mkdir(parents=True)
        model.write_bytes(b"weights")
        assert client.get("/api/images/status").json()["ready"] is True

        argv = engine.command("a red fox", "", 7, tmp_path / "out.png")
        assert argv[0] == str(sd) and argv[argv.index("-m") + 1] == str(model)
        assert argv[argv.index("--steps") + 1] == "4" and argv[argv.index("-s") + 1] == "7"
        assert "--vae-tiling" in argv

        real = engine.command
        monkeypatch.setattr(
            engine, "command", lambda *a: [sys.executable, str(script), *real(*a)[1:]]
        )
        cid = client.post("/api/conversations", json={"title": "x"}).json()["id"]
        made = client.post(
            "/api/images/generate", json={"conversation_id": cid, "prompt": "a red fox"}
        ).json()
        assert made["attachment"]["source"] == "generated"
        assert client.get(made["attachment"]["url"]).content.startswith(b"\x89PNG")
        assert engine.step == engine.total == 4  # progress was read as it ran

        messages = client.get(f"/api/conversations/{cid}").json()["messages"]
        ask, answer = messages[-2], messages[-1]
        assert ask["content"] == "a red fox" and answer["parent_id"] == ask["id"]
        assert [a["id"] for a in answer["attachments"]] == [made["attachment"]["id"]]


def test_not_set_up_says_where_to_set_it_up(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        cid = client.post("/api/conversations", json={"title": "x"}).json()["id"]
        refused = client.post(
            "/api/images/generate", json={"conversation_id": cid, "prompt": "a fox"}
        )
        assert refused.status_code == 503
        assert "get it in Images" in refused.json()["message"]


def test_a_model_in_parts_gets_each_part_under_its_flag(settings: Settings, tmp_path: Path) -> None:
    sd = runtime.folder(settings.paths.models_dir) / "sd.exe"
    sd.parent.mkdir(parents=True)
    sd.write_bytes(b"MZ")
    engine = ImageEngine(settings)
    flux = catalog.entry("flux-schnell") or {}
    for spec in parts.files(flux):
        target = parts.path(settings.paths.models_dir, spec)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"w")
    assert engine.installed("flux-schnell") and not engine.installed("z-image-turbo")
    argv = engine.command("a fox", "", 1, tmp_path / "o.png", "flux-schnell")
    for flag in ("--diffusion-model", "--vae", "--clip_l", "--t5xxl"):
        assert argv[argv.index(flag) + 1].startswith(str(parts.folder(settings.paths.models_dir)))
    assert "-m" not in argv and "-M" not in argv and "--clip-on-cpu" in argv
    # Z-Image shares FLUX's VAE: one file on disk, already here.
    zvae = (catalog.entry("z-image-turbo") or {})["parts"]["vae"]
    assert parts.path(settings.paths.models_dir, zvae).is_file()


def test_video_runs_in_video_mode(settings: Settings, tmp_path: Path) -> None:
    sd = runtime.folder(settings.paths.models_dir) / "sd.exe"
    sd.parent.mkdir(parents=True)
    sd.write_bytes(b"MZ")
    engine = ImageEngine(settings)
    key = catalog.video_key()
    assert key is not None
    for spec in parts.files(catalog.entry(key) or {}):
        target = parts.path(settings.paths.models_dir, spec)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"w")
    argv = engine.command("a cat", "", 1, tmp_path / "o.webm", key)
    assert argv[1:5] == ["-M", "vid_gen", "--video-frames", "33"]
    assert argv[argv.index("-n") + 1].startswith("blurry") and "--flow-shift" in argv
    assert engine.status().video_ready and not engine.status().ready  # pictures still need a model
