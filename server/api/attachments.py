"""Images for a conversation: upload one, show one, or take a screenshot."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from server import attachments, screen
from server.deps import State
from server.errors import NotFound, SovereignError
from server.models.attachments import Attachment

router = APIRouter(prefix="/api", tags=["attachments"])


@router.post("/attachments")
async def upload(request: Request, state: State) -> Attachment:
    """The image itself as the request body. Only PNG, JPEG, GIF and WebP get through."""
    data = await request.body()
    try:
        with state.db.session() as conn:
            return attachments.save(conn, state.settings.paths.data_dir, data)
    except ValueError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc


@router.get("/attachments/{attachment_id}")
def show(attachment_id: str, state: State) -> FileResponse:
    with state.db.session() as conn:
        found = attachments.get(conn, attachment_id)
    path = (
        attachments.path_for(state.settings.paths.data_dir, found.id, found.mime) if found else None
    )
    if found is None or path is None or not path.is_file():
        raise NotFound("Image")
    return FileResponse(path, media_type=found.mime)


@router.post("/screen/capture")
async def capture(state: State) -> Attachment:
    """What is on the primary display right now, as an image ready to ask about."""
    try:
        png = await asyncio.to_thread(screen.grab_png)
    except screen.NoScreen as exc:
        raise SovereignError("provider_unavailable", str(exc), status_code=503) from exc
    with state.db.session() as conn:
        return attachments.save(conn, state.settings.paths.data_dir, png, source="screen")
