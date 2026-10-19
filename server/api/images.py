"""Making pictures on this PC: set it up once, then ask for one in any chat."""

from __future__ import annotations

import time

from fastapi import APIRouter

from server import attachments
from server.chat import titles
from server.db import repo
from server.deps import State
from server.errors import NotFound, SovereignError
from server.imagegen.engine import ImageError
from server.models.conversation import ConversationUpdate
from server.models.images import (
    GalleryItem,
    Generated,
    GenerateRequest,
    ImageStatus,
    InstallRequest,
)

router = APIRouter(prefix="/api/images", tags=["images"])
CHOSEN = "image_model"


@router.get("/status")
def status(state: State) -> ImageStatus:
    assert state.images is not None
    return state.images.status()


@router.post("/install")
async def install(body: InstallRequest, state: State) -> ImageStatus:
    """Fetch stable-diffusion.cpp (if missing) and this model. Only when you press the button."""
    assert state.images is not None
    try:
        result = state.images.install(body.model)
    except ImageError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc
    with state.db.session() as conn:
        repo.settings.put(conn, CHOSEN, body.model)
    return result


@router.post("/generate")
async def generate(body: GenerateRequest, state: State) -> Generated:
    """The prompt becomes your message; the picture is the answer, kept in the chat."""
    assert state.images is not None
    prompt = body.prompt.strip()
    if not prompt:
        raise SovereignError("invalid_request", "Describe the picture you want.")
    with state.db.session() as conn:
        conversation = repo.conversations.get(conn, body.conversation_id)
    if conversation is None:
        raise NotFound("Conversation")
    started = time.monotonic()
    try:
        png = await state.images.generate(prompt, body.negative, body.seed)
    except ImageError as exc:
        raise SovereignError("provider_unavailable", str(exc), status_code=503) from exc
    data_dir = state.settings.paths.data_dir
    with state.db.session() as conn:
        if titles.needs_title(conversation.title):
            repo.conversations.update(
                conn, conversation.id, ConversationUpdate(title=titles.instant(prompt))
            )
        ask = repo.messages.create(
            conn,
            conversation_id=conversation.id,
            role="user",
            content=prompt,
            parent_id=conversation.active_leaf_id,
        )
        answer = repo.messages.create(
            conn,
            conversation_id=conversation.id,
            role="assistant",
            content="",
            parent_id=ask.id,
            model_id=f"image:{state.settings.images.model}",
        )
        picture = attachments.save(conn, data_dir, png, source="generated")
        attachments.link(conn, [picture.id], conversation.id, answer.id)
        repo.conversations.touch(conn, conversation.id, active_leaf_id=answer.id)
        linked = attachments.get(conn, picture.id)
    assert linked is not None
    return Generated(
        conversation_id=conversation.id,
        message_id=answer.id,
        attachment=linked,
        seconds=round(time.monotonic() - started, 1),
    )


@router.get("/gallery")
def gallery(state: State, limit: int = 120) -> list[GalleryItem]:
    """Every picture made here, newest first, with the description that made it."""
    with state.db.session() as conn:
        rows = conn.execute(
            "SELECT a.id AS attachment_id, a.conversation_id AS conversation_id,"
            " COALESCE(u.content, '') AS prompt, a.created_at AS created_at"
            " FROM attachments a"
            " LEFT JOIN messages m ON m.id = a.message_id"
            " LEFT JOIN messages u ON u.id = m.parent_id"
            " WHERE a.source = 'generated' AND a.conversation_id IS NOT NULL"
            " ORDER BY a.created_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        )
        return [GalleryItem(**dict(r)) for r in rows]
