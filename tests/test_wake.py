"""The wake word: audio in over a loopback socket, one "wake" out per "Hey Jarvis"."""

from __future__ import annotations

import os
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.main import create_app
from server.settings import Settings
from server.voice import wake


class Stub:
    """Scores scripted per chunk, standing in for the ONNX models."""

    def __init__(self, folder: Path) -> None:
        self.scores = iter([0.1, 0.9, 0.95, 0.2, 0.1])

    def feed(self, audio: np.ndarray) -> list[float]:
        return [next(self.scores, 0.0) for _ in range(len(audio) // wake.CHUNK)]


def test_one_hey_jarvis_wakes_once(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wake, "installed", lambda folder: True)
    monkeypatch.setattr(wake, "Detector", Stub)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/voice/wake").json()["phrase"] == "Hey Jarvis"
        with client.websocket_connect("/api/voice/wake/listen") as socket:
            chunk = np.zeros(wake.CHUNK, dtype=np.int16).tobytes()
            socket.send_bytes(chunk)  # 0.1: nothing
            socket.send_bytes(chunk + chunk)  # 0.9 then 0.95: one wake, at its peak
            assert socket.receive_json() == {"wake": True, "score": 0.95}
            socket.send_bytes(chunk)  # 0.2: the tail of the same phrase, quiet


def test_listening_refuses_until_installed(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/voice/wake").json()["installed"] is False
        with client.websocket_connect("/api/voice/wake/listen") as socket:
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
            assert closed.value.code == 4404


MODELS = Path(os.environ.get("JARVIS_WAKE_MODELS", "models/wake"))


@pytest.mark.skipif(not (MODELS / "alexa_test.wav").is_file(), reason="needs the wake models")
def test_the_real_models_hear_their_word_and_only_it() -> None:
    """With openWakeWord's own test clip: its model scores ~1, a different word's ~0. The
    front end (mel + embedding) is shared, so this checks the streaming that "Hey Jarvis" uses."""
    with wave.open(str(MODELS / "alexa_test.wav")) as handle:
        clip = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16)
    audio = np.concatenate((np.zeros(16000, np.int16), clip, np.zeros(16000, np.int16)))

    def best(model: str) -> float:
        detector = wake.Detector(MODELS, model)
        return max(
            s for i in range(0, len(audio), 1600) for s in detector.feed(audio[i : i + 1600])
        )

    assert best("alexa_v0.1.onnx") > 0.9
    assert best(wake.WAKE_MODEL) < 0.1
