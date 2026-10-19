"""Kokoro: the natural voice. An 82M-parameter model (Apache 2.0) that sounds like a person reading,
where Piper sounds like a machine reading well. Fetched from inside the app when you ask for it -
about 120 MB, the int8 build - and run on the CPU with the ONNX Runtime voice already uses.

Kokoro speaks from phonemes; kokoro-onnx turns text into them with espeak-ng, which ships in its
own wheel. Text is cleaned first (server/voice/spoken.py), so emoji and markdown never reach it.
Your choice of engine and voice lives in `data/voice.json`, beside everything else you chose.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np

from server.settings import Settings

RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL = "kokoro-v1.0.int8.onnx"
VOICES_FILE = "voices-v1.0.bin"
FILES = {
    MODEL: "6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb",
    VOICES_FILE: "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
"""Pinned by sha256: a download only counts once it matches."""
SAMPLE_RATE = 24_000
DEFAULT_VOICE = "af_heart"

VOICES: list[tuple[str, str]] = [
    ("af_heart", "Heart - warm, American. The most natural of them."),
    ("af_bella", "Bella - bright, American"),
    ("af_nicole", "Nicole - soft, close, American"),
    ("am_michael", "Michael - calm, American"),
    ("am_fenrir", "Fenrir - deep, American"),
    ("bm_george", "George - British, the butler you'd expect"),
    ("bm_fable", "Fable - British, a storyteller"),
    ("bf_emma", "Emma - British"),
    ("ef_dora", "Dora - Spanish"),
    ("em_alex", "Alex - Spanish"),
]
LANGUAGES = {
    "a": "en-us",
    "b": "en-gb",
    "e": "es",
    "f": "fr-fr",
    "i": "it",
    "p": "pt-br",
    "h": "hi",
}

_engine: Any = None
_lock = asyncio.Lock()


def folder(settings: Settings) -> Path:
    return settings.paths.models_dir / "kokoro"


def installed(settings: Settings) -> bool:
    return all((folder(settings) / name).is_file() for name in FILES)


def library_available() -> bool:
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        return False
    return True


def _choice_file(settings: Settings) -> Path:
    return settings.paths.data_dir / "voice.json"


def choice(settings: Settings) -> dict[str, str]:
    """{"engine": "kokoro" | "piper", "voice": <kokoro voice>}."""
    try:
        saved = json.loads(_choice_file(settings).read_text())
    except (OSError, ValueError):
        saved = {}
    voice = saved.get("voice") if saved.get("voice") in dict(VOICES) else DEFAULT_VOICE
    return {"engine": "kokoro" if saved.get("engine") == "kokoro" else "piper", "voice": voice}


def choose(settings: Settings, *, engine: str | None = None, voice: str | None = None) -> None:
    current = choice(settings)
    if engine in ("kokoro", "piper"):
        current["engine"] = engine
    if voice in dict(VOICES):
        current["voice"] = voice
    path = _choice_file(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current))


def active(settings: Settings) -> bool:
    """Kokoro speaks when it is chosen, downloaded, and in this build."""
    return choice(settings)["engine"] == "kokoro" and installed(settings) and library_available()


def unload() -> None:
    global _engine
    _engine = None


async def prepare(settings: Settings) -> Any:
    """Load the model now, so a speak request fails before its response starts, not halfway."""
    return await _load(settings)


async def _load(settings: Settings) -> Any:
    global _engine
    async with _lock:
        if _engine is None:
            from kokoro_onnx import Kokoro

            base = folder(settings)
            _engine = await asyncio.to_thread(Kokoro, str(base / MODEL), str(base / VOICES_FILE))
        return _engine


def _pcm(samples: np.ndarray) -> bytes:
    return (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()


async def synthesize(settings: Settings, sentence: str, voice: str | None = None) -> bytes:
    """One sentence as 16-bit mono PCM at 24 kHz."""
    engine = await _load(settings)
    name = voice if voice in dict(VOICES) else choice(settings)["voice"]
    speed = 1.0 / max(0.5, min(settings.voice.tts_length_scale, 2.0))
    samples, _ = await asyncio.to_thread(
        engine.create, sentence, voice=name, speed=speed, lang=LANGUAGES.get(name[0], "en-us")
    )
    return _pcm(samples)
