"""The natural voice: chosen in Settings, used for every way Jarvis speaks once it is downloaded,
fed clean text (no emoji, no markdown), and streamed a sentence at a time at Kokoro's 24 kHz."""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server.main import create_app
from server.settings import Settings
from server.voice import capability, kokoro

REAL = os.environ.get("KOKORO_DIR", "")


class FakeKokoro:
    def __init__(self) -> None:
        self.said: list[tuple[str, str, str]] = []

    def create(self, text: str, voice: str, speed: float, lang: str) -> tuple[Any, int]:
        self.said.append((text, voice, lang))
        return np.zeros(2400, dtype=np.float32), kokoro.SAMPLE_RATE


def _install(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> FakeKokoro:
    folder = kokoro.folder(settings)
    folder.mkdir(parents=True)
    for name in kokoro.FILES:
        (folder / name).write_bytes(b"x")
    fake = FakeKokoro()
    monkeypatch.setattr(kokoro, "_engine", fake)
    monkeypatch.setattr(kokoro, "library_available", lambda: True)
    return fake


def test_piper_until_kokoro_is_chosen_and_downloaded(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert kokoro.choice(settings) == {"engine": "piper", "voice": kokoro.DEFAULT_VOICE}
    kokoro.choose(settings, engine="kokoro")
    assert not kokoro.active(settings)  # chosen, but not downloaded
    _install(settings, monkeypatch)
    assert kokoro.active(settings)
    assert capability.tts_status(settings).engine == "kokoro"


def test_speaking_uses_kokoro_with_clean_text(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _install(settings, monkeypatch)
    kokoro.choose(settings, engine="kokoro", voice="bm_george")
    with TestClient(create_app(settings)) as client:
        wav = client.post("/api/voice/speak", json={"text": "**Done** 🎉. All saved!"}).content
    assert struct.unpack("<I", wav[24:28])[0] == kokoro.SAMPLE_RATE
    assert len(wav) == 44 + 2 * 2400 * 2  # two sentences
    assert [s for s, _, _ in fake.said] == ["Done.", "All saved!"]
    assert fake.said[0][1:] == ("bm_george", "en-gb")


def test_settings_page_lists_voices_and_saves_the_choice(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    with TestClient(create_app(settings)) as client:
        status = client.get("/api/voice/kokoro").json()
        assert not status["installed"] and ["af_heart", status["voices"][0][1]] in status["voices"]
        client.put("/api/voice/kokoro", json={"voice": "am_michael", "engine": "kokoro"})
    assert kokoro.choice(settings) == {"engine": "kokoro", "voice": "am_michael"}


@pytest.mark.skipif(not REAL, reason="set KOKORO_DIR to a folder holding the real model files")
def test_the_real_model_speaks(settings: Settings) -> None:
    import asyncio

    folder = kokoro.folder(settings)
    folder.mkdir(parents=True)
    for name in kokoro.FILES:
        (folder / name).symlink_to(Path(REAL) / name)
    kokoro.unload()
    pcm = asyncio.run(kokoro.synthesize(settings, "Good afternoon, Nick."))
    assert len(pcm) > kokoro.SAMPLE_RATE  # more than half a second of speech
