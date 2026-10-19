"""Settings > Data: what is stored, and clearing it."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from server import data_admin
from server.data_admin import DataKind, Kind
from server.deps import State

router = APIRouter(prefix="/api/data", tags=["data"])


class ClearRequest(BaseModel):
    kind: Kind


@router.get("")
def usage(state: State) -> list[DataKind]:
    return data_admin.usage(state)


@router.post("/clear")
async def clear(body: ClearRequest, state: State) -> list[DataKind]:
    if body.kind == "chats":
        data_admin.clear_chats(state)
    elif body.kind == "memory":
        data_admin.clear_memory(state)
    elif body.kind == "knowledge":
        data_admin.clear_knowledge(state)
    elif body.kind == "cache":
        data_admin.clear_cache(state)
    elif body.kind == "models":
        await data_admin.clear_models(state)
    else:
        data_admin.clear_everything(state)
    return data_admin.usage(state)
