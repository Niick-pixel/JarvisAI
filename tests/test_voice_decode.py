"""Our own audio decode: what the browser records, as the 16kHz mono samples Whisper reads."""

from __future__ import annotations

import io
import wave

import numpy as np
import pytest


def test_stereo_wav_at_22khz_becomes_16khz_mono_floats() -> None:
    pytest.importorskip("av")
    from server.voice.stt import decode

    buf = io.BytesIO()
    with wave.open(buf, "wb") as clip:
        clip.setnchannels(2)
        clip.setsampwidth(2)
        clip.setframerate(22050)
        clip.writeframes((np.sin(np.arange(44100) / 10) * 8000).astype(np.int16).tobytes())
    samples = decode(buf.getvalue())
    assert samples.dtype == np.float32 and samples.shape == (16000,)  # one second
    assert 0.2 < float(np.abs(samples).max()) <= 1.0
