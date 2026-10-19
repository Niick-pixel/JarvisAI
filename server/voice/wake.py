"""The wake word: "Hey Jarvis", heard on this PC by a 1 MB model, and nothing else.

openWakeWord's published pipeline, run on the onnxruntime the voice pack already ships with,
rather than through the openwakeword package (which would add scipy and scikit-learn to the
bundle for three matrix multiplications). Three small models, in order:

1. melspectrogram.onnx - raw 16 kHz audio to 32-band mel frames, one every 10 ms
2. embedding_model.onnx - each 76-frame (~775 ms) window to a 96-number embedding
3. hey_jarvis_v0.1.onnx - the last 16 embeddings (~1.3 s) to a 0-1 score

Audio arrives in 80 ms chunks (1280 samples); each chunk yields one score. The streaming is the
reference implementation's, step for step (openwakeword/utils.py, AudioFeatures), so a model that
scores well there scores the same here. Nothing about the audio is kept: the buffers hold the last
ten seconds at most, in memory, and are dropped when listening stops.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

CHUNK = 1280
"""80 ms at 16 kHz: the step the models were trained on."""
WINDOW = 76
FEATURES = 16
MEL_MAX = 10 * 97
FEATURE_MAX = 120
FILES = {
    "melspectrogram.onnx": "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",
    "embedding_model.onnx": "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",
    "hey_jarvis_v0.1.onnx": "94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb",
}
"""The files, pinned by sha256: a download only counts once it matches."""
RELEASE = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
WAKE_MODEL = "hey_jarvis_v0.1.onnx"


def installed(folder: Path) -> bool:
    return all((folder / name).is_file() for name in FILES)


def _session(path: Path) -> Any:
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.inter_op_num_threads = 1
    options.intra_op_num_threads = 1
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


class Detector:
    """One listener's state. Feed it int16 PCM at 16 kHz; it returns a score per 80 ms."""

    def __init__(self, folder: Path, model: str = WAKE_MODEL) -> None:
        self.mel_model = _session(folder / "melspectrogram.onnx")
        self.embed_model = _session(folder / "embedding_model.onnx")
        self.wake_model = _session(folder / model)
        self.wake_input = self.wake_model.get_inputs()[0].name
        self.raw: deque[int] = deque(maxlen=16000 * 10)
        self.pending = np.empty(0, dtype=np.int16)
        self.mel = np.ones((WINDOW, 32), dtype=np.float32)
        # Seeded with noise, as the reference is, so the first second scores like any other.
        noise = np.random.default_rng(0).integers(-1000, 1000, 16000 * 4).astype(np.int16)
        self.features = self._embed_clip(noise)

    def _melspectrogram(self, audio: np.ndarray) -> np.ndarray:
        out = self.mel_model.run(None, {"input": audio.astype(np.float32)[None, :]})
        return np.squeeze(out[0]) / 10 + 2

    def _embed(self, windows: np.ndarray) -> np.ndarray:
        out = self.embed_model.run(None, {"input_1": windows[..., None].astype(np.float32)})
        return np.asarray(out[0]).reshape(-1, 96)

    def _embed_clip(self, audio: np.ndarray) -> np.ndarray:
        spec = self._melspectrogram(audio)
        windows = [spec[i : i + WINDOW] for i in range(0, spec.shape[0], 8)]
        return self._embed(np.array([w for w in windows if w.shape[0] == WINDOW]))

    def _score(self) -> float:
        x = self.features[-FEATURES:][None, :, :].astype(np.float32)
        return float(np.asarray(self.wake_model.run(None, {self.wake_input: x})[0]).ravel()[0])

    def feed(self, audio: np.ndarray) -> list[float]:
        """Scores for every whole 80 ms chunk now available, oldest first."""
        audio = np.concatenate((self.pending, audio.astype(np.int16)))
        whole = len(audio) - len(audio) % CHUNK
        self.pending = audio[whole:]
        scores: list[float] = []
        for start in range(0, whole, CHUNK):
            self.raw.extend(audio[start : start + CHUNK].tolist())
            recent = np.fromiter(self.raw, dtype=np.int16)[-(CHUNK + 160 * 3) :]
            self.mel = np.vstack((self.mel, self._melspectrogram(recent)))[-MEL_MAX:]
            if self.mel.shape[0] >= WINDOW:
                embedding = self._embed(self.mel[-WINDOW:][None, :, :])
                self.features = np.vstack((self.features, embedding))[-FEATURE_MAX:]
            scores.append(self._score())
        return scores
