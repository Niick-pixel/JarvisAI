"""Local speech in and out. Both engines are optional, and say so rather than failing silently."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from server.deps import State
from server.errors import SovereignError
from server.models.voice import SpeakRequest, Transcript, VoicePackProgress, VoiceStatus
from server.voice import capability, kokoro, stt, tts
from server.voice.capability import VoiceUnavailable

router = APIRouter(prefix="/api/voice", tags=["voice"])

WAV_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "A WAV stream, one PCM block per sentence.",
        "content": {"audio/wav": {}},
    }
}


@router.get("/status")
def status(state: State) -> VoiceStatus:
    """Which half of voice works, on what device, and the exact command that fixes the rest."""
    return capability.status(state.settings, stt_device=stt.loaded_device())


@router.get("/pack")
async def pack_progress(state: State) -> VoicePackProgress:
    assert state.voice_pack is not None
    return state.voice_pack.progress


@router.post("/pack")
async def pack_start(state: State) -> VoicePackProgress:
    """Fetch the Whisper model and Piper voice the settings name - nothing else, and only now."""
    assert state.voice_pack is not None
    return state.voice_pack.start()


@router.delete("/pack")
async def pack_cancel(state: State) -> VoicePackProgress:
    assert state.voice_pack is not None
    state.voice_pack.cancel()
    return state.voice_pack.progress


@router.post("/transcribe")
async def transcribe(request: Request, state: State) -> Transcript:
    """The raw recording as the request body. Whatever the browser captured, PyAV decodes.

    Taking bytes rather than a multipart form is not laziness: multipart would pull in another
    dependency to carry one field.
    """
    audio = await request.body()
    try:
        return await stt.transcribe(state.settings, audio)
    except VoiceUnavailable as exc:
        raise _unavailable(exc) from exc
    except ValueError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc


@router.post("/speak", responses=WAV_RESPONSES)
async def speak(body: SpeakRequest, state: State) -> StreamingResponse:
    if not body.text.strip():
        raise SovereignError("invalid_request", "Nothing to speak.")
    try:
        # Resolve the voice before the response begins: once bytes are on the wire an error can
        # only be a truncated stream, which sounds like a bug rather than reading like one.
        if body.voice is None and kokoro.active(state.settings):
            await kokoro.prepare(state.settings)
        else:
            await tts.voice_for(state.settings, body.voice)
    except VoiceUnavailable as exc:
        raise _unavailable(exc) from exc
    return StreamingResponse(
        tts.stream_wav(state.settings, body.text, body.voice),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


class KokoroStatus(BaseModel):
    installed: bool
    in_this_build: bool
    engine: str
    voice: str
    voices: list[list[str]]
    """[id, description] pairs, in the order Settings shows them."""
    download: VoicePackProgress


class KokoroChoice(BaseModel):
    engine: Literal["kokoro", "piper"] | None = None
    voice: str | None = None


def _kokoro_status(state: State) -> KokoroStatus:
    assert state.kokoro_pack is not None
    chosen = kokoro.choice(state.settings)
    return KokoroStatus(
        installed=kokoro.installed(state.settings),
        in_this_build=kokoro.library_available(),
        engine=chosen["engine"],
        voice=chosen["voice"],
        voices=[[v, d] for v, d in kokoro.VOICES],
        download=state.kokoro_pack.progress,
    )


@router.get("/kokoro")
def kokoro_status(state: State) -> KokoroStatus:
    return _kokoro_status(state)


@router.post("/kokoro/download")
async def kokoro_download(state: State) -> KokoroStatus:
    """Fetch the natural voice (about 120 MB). Only when you press the button."""
    assert state.kokoro_pack is not None
    state.kokoro_pack.start()
    return _kokoro_status(state)


@router.put("/kokoro")
def kokoro_choose(body: KokoroChoice, state: State) -> KokoroStatus:
    kokoro.choose(state.settings, engine=body.engine, voice=body.voice)
    return _kokoro_status(state)


@router.get("/kokoro/preview", responses=WAV_RESPONSES)
async def kokoro_preview(voice: str, state: State) -> Response:
    """A sentence in one voice, so you can hear it before choosing it."""
    if not kokoro.installed(state.settings) or not kokoro.library_available():
        raise SovereignError(
            "provider_unavailable", "Get the natural voice first.", status_code=503
        )
    pcm = await kokoro.synthesize(state.settings, PREVIEW, voice)
    return Response(
        tts.wav_header(kokoro.SAMPLE_RATE) + pcm,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


PREVIEW = "Hello. I'm Jarvis, and this is how I'll sound when I talk to you."


def _unavailable(exc: VoiceUnavailable) -> SovereignError:
    detail = f"{exc.reason} Fix: {exc.fix}" if exc.fix else exc.reason
    return SovereignError("provider_unavailable", detail, status_code=503)
